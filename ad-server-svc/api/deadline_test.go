package api

import (
	"context"
	"net/http"
	"testing"
	"time"
)

// hangingStore never answers. It only returns when the request's deadline cancels the call.
type hangingStore struct {
	*fakeStore
}

func (h hangingStore) Get(ctx context.Context, _ string) (string, error) {
	<-ctx.Done()
	return "", ctx.Err()
}

func TestAdserve_ASlowRedisCannotHoldARequestPastItsDeadline(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server := newTestServer(t, hangingStore{store}, adManager(t).URL)
	server.config.RedisTimeout = 50 * time.Millisecond

	start := time.Now()
	recorder := serve(t, server, validQuery, slotRequest())
	took := time.Since(start)

	if recorder.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500 when Redis does not answer in time", recorder.Code)
	}
	if took > 2*time.Second {
		t.Errorf("the request took %v, want it to give up soon after the 50ms deadline", took)
	}
}
