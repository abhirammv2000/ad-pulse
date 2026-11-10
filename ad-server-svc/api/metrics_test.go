package api

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"adserver/cache"

	"github.com/prometheus/client_golang/prometheus/testutil"
)

// The metrics are global, so these tests compare counts before and after a request.

func TestMetrics_RequestsAreCountedByResult(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server := newTestServer(t, store, adManager(t).URL)

	bids := testutil.ToFloat64(adRequests.WithLabelValues("bid"))
	noBids := testutil.ToFloat64(adRequests.WithLabelValues("no_bid"))
	badRequests := testutil.ToFloat64(adRequests.WithLabelValues("bad_request"))

	serve(t, server, validQuery, slotRequest())
	serve(t, server, validQuery, requestForASizeNothingFits())
	serve(t, server, "publisher_id=P1", slotRequest()) // no ad unit, so a 400

	if got := testutil.ToFloat64(adRequests.WithLabelValues("bid")) - bids; got != 1 {
		t.Errorf("bid requests went up by %v, want 1", got)
	}
	if got := testutil.ToFloat64(adRequests.WithLabelValues("no_bid")) - noBids; got != 1 {
		t.Errorf("no_bid requests went up by %v, want 1", got)
	}
	if got := testutil.ToFloat64(adRequests.WithLabelValues("bad_request")) - badRequests; got != 1 {
		t.Errorf("bad_request requests went up by %v, want 1", got)
	}
}

// requestForASizeNothingFits asks for a slot no cached creative fits, so nothing is bid.
func requestForASizeNothingFits() cache.RequestBody {
	return cache.RequestBody{ID: "req1", Imp: []cache.Impression{impression("imp1", 728, 90)}}
}

func TestMetrics_SkippedAdsAreCountedByReason(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store,
		budgetedAd("SPENT", 1, 10*dollar),
		cappedAd("CAPPED", 2, freqCap("AD", "CSC", 1, "DAY", 1)),
	)
	store.values["spend:ad:SPENT"] = "10000000000"
	store.addEvent("fc:AD:CAPPED:CSC:alice", "bid1", testNow-10)
	server := budgetServer(t, store)

	spent := testutil.ToFloat64(adsSkipped.WithLabelValues("total_budget"))
	capped := testutil.ToFloat64(adsSkipped.WithLabelValues("frequency_cap"))
	anonymous := testutil.ToFloat64(adsSkipped.WithLabelValues("no_user_id"))

	servedTo(t, server, "alice")
	servedTo(t, server, "")

	if got := testutil.ToFloat64(adsSkipped.WithLabelValues("total_budget")) - spent; got != 2 {
		t.Errorf("total_budget skips went up by %v, want 2, one for each request", got)
	}
	if got := testutil.ToFloat64(adsSkipped.WithLabelValues("frequency_cap")) - capped; got != 1 {
		t.Errorf("frequency_cap skips went up by %v, want 1", got)
	}
	if got := testutil.ToFloat64(adsSkipped.WithLabelValues("no_user_id")) - anonymous; got != 1 {
		t.Errorf("no_user_id skips went up by %v, want 1", got)
	}
}

func TestMetrics_AreServedAtSlashMetrics(t *testing.T) {
	server := newTestServer(t, newFakeStore(), adManager(t).URL)
	serve(t, server, validQuery, slotRequest())

	recorder := httptest.NewRecorder()
	server.router.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/metrics", nil))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d", recorder.Code)
	}
	for _, name := range []string{"adserver_requests_total", "adserver_request_duration_seconds_bucket"} {
		if !strings.Contains(recorder.Body.String(), name) {
			t.Errorf("/metrics has no %s", name)
		}
	}
}
