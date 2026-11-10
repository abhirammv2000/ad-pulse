package services

import (
	"errors"
	"testing"
	"time"

	"github.com/prometheus/client_golang/prometheus/testutil"
)

// The counter is global, so the test compares counts before and after.
func TestCounted_CountsEachPingByEventAndResult(t *testing.T) {
	count := func(event, result string) float64 {
		return testutil.ToFloat64(events.WithLabelValues(event, result))
	}
	before := map[string]float64{
		"accepted":       count("click", "accepted"),
		"bad_signature":  count("click", "bad_signature"),
		"too_old":        count("render", "too_old"),
		"bad_request":    count("render", "bad_request"),
		"publish_failed": count("click", "publish_failed"),
	}

	click := Counted("click", engagementHandler(&fakePublisher{}, "clicks", "secret"))
	render := Counted("render", engagementHandler(&fakePublisher{}, "renders", ""))
	failing := Counted("click", engagementHandler(&fakePublisher{err: errors.New("down")}, "clicks", ""))

	_, encoded := freshSignedIID()
	serve(click, signedQuery("secret", encoded))                               // accepted
	serve(click, iidQuery(freshIID("AD1")))                                    // no signature
	serve(render, iidQuery(iidServedAt("AD1", time.Now().Add(-25*time.Hour)))) // served too long ago
	serve(render, "?iid=not!base64")                                           // bad request
	serve(failing, iidQuery(freshIID("AD1")))                                  // Pub/Sub failed

	after := map[string]float64{
		"accepted":       count("click", "accepted"),
		"bad_signature":  count("click", "bad_signature"),
		"too_old":        count("render", "too_old"),
		"bad_request":    count("render", "bad_request"),
		"publish_failed": count("click", "publish_failed"),
	}
	for result := range before {
		if got := after[result] - before[result]; got != 1 {
			t.Errorf("%s went up by %v, want 1", result, got)
		}
	}
}
