package services

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// events counts click and render pings. Both labels have fixed values, so no ping
// can create new series.
var events = promauto.NewCounterVec(prometheus.CounterOpts{
	Name: "engagement_events_total",
	Help: "Click and render pings by event and result: accepted, bad_signature, too_old, bad_request, publish_failed or error.",
}, []string{"event", "result"})

// eventResult names what happened to a ping from the status the handler answered.
func eventResult(status int) string {
	switch status {
	case http.StatusOK:
		return "accepted"
	case http.StatusForbidden:
		return "bad_signature"
	case http.StatusGone:
		return "too_old"
	case http.StatusBadRequest:
		return "bad_request"
	case http.StatusBadGateway:
		return "publish_failed"
	}
	return "error"
}

// Counted wraps an engagement handler so every ping it answers is counted.
func Counted(event string, handler gin.HandlerFunc) gin.HandlerFunc {
	return func(ctx *gin.Context) {
		handler(ctx)
		events.WithLabelValues(event, eventResult(ctx.Writer.Status())).Inc()
	}
}
