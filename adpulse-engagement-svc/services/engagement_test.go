package services

import (
	"context"
	"encoding/base64"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
)

// iidServedAt is the iid of one bid for adID, served at the given time.
func iidServedAt(adID string, servedAt time.Time) string {
	return fmt.Sprintf(`{"bidid":"B-%s","adid":%q,"requesttimestamp":%d}`, adID, adID, servedAt.Unix())
}

// freshIID is an iid for an ad served just now.
func freshIID(adID string) string {
	return iidServedAt(adID, time.Now())
}

// iidQuery puts an iid in a query string the way the ad server does.
func iidQuery(iid string) string {
	return "?iid=" + url.QueryEscape(base64.StdEncoding.EncodeToString([]byte(iid)))
}

// fixClock makes the handlers see the given time for the rest of the test.
func fixClock(t *testing.T, at time.Time) {
	t.Helper()
	previous := now
	now = func() time.Time { return at }
	t.Cleanup(func() { now = previous })
}

type fakePublisher struct {
	published map[string][]byte
	err       error
}

func (f *fakePublisher) Publish(_ context.Context, topicID string, payload []byte) (string, error) {
	if f.err != nil {
		return "", f.err
	}
	if f.published == nil {
		f.published = make(map[string][]byte)
	}
	f.published[topicID] = payload
	return "msg-1", nil
}

func (f *fakePublisher) Close() error { return nil }

func serve(handler gin.HandlerFunc, query string) *httptest.ResponseRecorder {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/e", handler)

	recorder := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/e"+query, nil)
	router.ServeHTTP(recorder, req)
	return recorder
}

func TestEngagementHandlerPublishesDecodedIID(t *testing.T) {
	iid := freshIID("AD123")
	publisher := &fakePublisher{}

	recorder := serve(engagementHandler(publisher, "click-topic", ""), iidQuery(iid))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusOK)
	}
	if got := string(publisher.published["click-topic"]); got != iid {
		t.Errorf("published %q, want %q", got, iid)
	}
}

func TestEngagementHandlerRejectsBadInput(t *testing.T) {
	tests := []struct {
		name  string
		query string
	}{
		{"missing iid", ""},
		{"not base64", "?iid=not!base64"},
		{"not json", iidQuery("plain text")},
		{"a json list", iidQuery("[1]")},
		{"no bid id", iidQuery(fmt.Sprintf(`{"adid":"AD1","requesttimestamp":%d}`, time.Now().Unix()))},
		{"no serve time", iidQuery(`{"bidid":"B1","adid":"AD1"}`)},
		{"served in the future", iidQuery(iidServedAt("AD1", time.Now().Add(time.Hour)))},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			publisher := &fakePublisher{}
			recorder := serve(engagementHandler(publisher, "click-topic", ""), tt.query)

			if recorder.Code != http.StatusBadRequest {
				t.Errorf("status = %d, want %d", recorder.Code, http.StatusBadRequest)
			}
			if len(publisher.published) != 0 {
				t.Errorf("published %d messages, want 0", len(publisher.published))
			}
		})
	}
}

func TestEngagementHandlerChecksHowLongAgoTheAdWasServed(t *testing.T) {
	served := time.Date(2026, 11, 8, 12, 0, 0, 0, time.UTC)
	cases := []struct {
		name  string
		at    time.Time
		want  int
		count int
	}{
		{"just served", served, http.StatusOK, 1},
		{"a second inside the 24 hours", served.Add(24*time.Hour - time.Second), http.StatusOK, 1},
		{"a second past the 24 hours", served.Add(24*time.Hour + time.Second), http.StatusGone, 0},
		{"this clock is behind the ad server's by less than the allowed skew", served.Add(-4 * time.Minute), http.StatusOK, 1},
		{"this clock is behind by more than the allowed skew", served.Add(-6 * time.Minute), http.StatusBadRequest, 0},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			fixClock(t, c.at)
			publisher := &fakePublisher{}

			recorder := serve(engagementHandler(publisher, "click-topic", ""), iidQuery(iidServedAt("AD1", served)))

			if recorder.Code != c.want {
				t.Errorf("status = %d, want %d: %s", recorder.Code, c.want, recorder.Body.String())
			}
			if len(publisher.published) != c.count {
				t.Errorf("published %d messages, want %d", len(publisher.published), c.count)
			}
		})
	}
}

func TestEngagementHandlerReportsPublishFailure(t *testing.T) {
	publisher := &fakePublisher{err: errors.New("pubsub unavailable")}

	recorder := serve(engagementHandler(publisher, "click-topic", ""), iidQuery(freshIID("AD123")))

	if recorder.Code != http.StatusBadGateway {
		t.Errorf("status = %d, want %d", recorder.Code, http.StatusBadGateway)
	}
}

func TestClickAndCSCUseDistinctTopics(t *testing.T) {
	t.Setenv("CLICK_TOPIC_ID", "clicks")
	t.Setenv("CSC_TOPIC_ID", "renders")

	iid := iidQuery(freshIID("AD123"))

	clickPublisher := &fakePublisher{}
	serve(ClickServiceHandler(clickPublisher), iid)
	if _, ok := clickPublisher.published["clicks"]; !ok {
		t.Errorf("click handler published to %v, want topic %q", clickPublisher.published, "clicks")
	}

	cscPublisher := &fakePublisher{}
	serve(CSCServiceHandler(cscPublisher), iid)
	if _, ok := cscPublisher.published["renders"]; !ok {
		t.Errorf("csc handler published to %v, want topic %q", cscPublisher.published, "renders")
	}
}
