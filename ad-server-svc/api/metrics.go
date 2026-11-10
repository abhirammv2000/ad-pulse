package api

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Prometheus metrics, served at /metrics. Every label has a fixed set of values, so
// no request can create new series.
var (
	adRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "adserver_requests_total",
		Help: "Ad requests by result: bid, no_bid, bad_request or error.",
	}, []string{"result"})

	adRequestSeconds = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "adserver_request_duration_seconds",
		Help:    "How long an ad request took to answer.",
		Buckets: []float64{.001, .0025, .005, .01, .025, .05, .1, .25, .5, 1},
	})

	adsSkipped = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "adserver_ads_skipped_total",
		Help: "Candidate ads left out of a request by the budget or frequency cap checks, by reason.",
	}, []string{"reason"})
)

// requestResult names the outcome of an ad request from its status code.
func requestResult(status int) string {
	switch {
	case status == http.StatusOK:
		return "bid"
	case status == http.StatusNoContent:
		return "no_bid"
	case status >= 400 && status < 500:
		return "bad_request"
	default:
		return "error"
	}
}

// measured wraps a handler to count its requests and time them.
func measured(handler gin.HandlerFunc) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		start := time.Now()
		handler(ctx)
		adRequestSeconds.Observe(time.Since(start).Seconds())
		adRequests.WithLabelValues(requestResult(ctx.Writer.Status())).Inc()
	}
}
