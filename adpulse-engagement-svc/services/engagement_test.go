package services

import (
	"context"
	"encoding/base64"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

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
	iid := `{"adid":"AD123","creativeid":"CR123"}`
	publisher := &fakePublisher{}

	recorder := serve(
		engagementHandler(publisher, "click-topic", ""),
		"?iid="+base64.StdEncoding.EncodeToString([]byte(iid)),
	)

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
		{"not json", "?iid=" + base64.StdEncoding.EncodeToString([]byte("plain text"))},
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

func TestEngagementHandlerReportsPublishFailure(t *testing.T) {
	publisher := &fakePublisher{err: errors.New("pubsub unavailable")}

	recorder := serve(
		engagementHandler(publisher, "click-topic", ""),
		"?iid="+base64.StdEncoding.EncodeToString([]byte(`{"adid":"AD123"}`)),
	)

	if recorder.Code != http.StatusBadGateway {
		t.Errorf("status = %d, want %d", recorder.Code, http.StatusBadGateway)
	}
}

func TestClickAndCSCUseDistinctTopics(t *testing.T) {
	t.Setenv("CLICK_TOPIC_ID", "clicks")
	t.Setenv("CSC_TOPIC_ID", "renders")

	iid := "?iid=" + base64.StdEncoding.EncodeToString([]byte(`{"adid":"AD123"}`))

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
