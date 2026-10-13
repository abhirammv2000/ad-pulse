package api

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"adserver/util"
)

// recordingManager answers 200 to the publisher and ad unit lookups and records the API key header of each call.
// When requireKey is set it answers 401 unless the header matches, the way the real manager does.
type recordingManager struct {
	mu         sync.Mutex
	keys       []string
	requireKey string
}

func (m *recordingManager) handler(w http.ResponseWriter, r *http.Request) {
	m.mu.Lock()
	m.keys = append(m.keys, r.Header.Get("X-API-Key"))
	m.mu.Unlock()
	if m.requireKey != "" && r.Header.Get("X-API-Key") != m.requireKey {
		w.WriteHeader(http.StatusUnauthorized)
		return
	}
	w.WriteHeader(http.StatusOK)
}

func serverWithKey(t *testing.T, managerURL, key string) *Server {
	t.Helper()
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server, err := NewServer(util.Config{
		AdManagerAddress: managerURL,
		AdManagerAPIKey:  key,
		ClickUrl:         "http://engagement/clk",
		RenderUrl:        "http://engagement/csc",
	}, store)
	if err != nil {
		t.Fatal(err)
	}
	return server
}

func TestAdserve_SendsTheAPIKeyOnBothManagerLookups(t *testing.T) {
	m := &recordingManager{requireKey: "secret"}
	manager := httptest.NewServer(http.HandlerFunc(m.handler))
	defer manager.Close()

	recorder := serve(t, serverWithKey(t, manager.URL, "secret"), validQuery, slotRequest())

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", recorder.Code, recorder.Body.String())
	}
	if len(m.keys) != 2 || m.keys[0] != "secret" || m.keys[1] != "secret" {
		t.Errorf("the manager saw keys %q, want the key on both the publisher and the ad unit lookup", m.keys)
	}
}

func TestAdserve_SendsNoKeyHeaderWhenNoneIsConfigured(t *testing.T) {
	m := &recordingManager{}
	manager := httptest.NewServer(http.HandlerFunc(m.handler))
	defer manager.Close()

	recorder := serve(t, serverWithKey(t, manager.URL, ""), validQuery, slotRequest())

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", recorder.Code)
	}
	for _, key := range m.keys {
		if key != "" {
			t.Errorf("an X-API-Key header was sent although no key is configured: %q", key)
		}
	}
}

func TestAdserve_ARejectedKeyIsABadGatewayNotAMissingPublisher(t *testing.T) {
	m := &recordingManager{requireKey: "the-right-key"}
	manager := httptest.NewServer(http.HandlerFunc(m.handler))
	defer manager.Close()

	for _, wrongKey := range []string{"the-wrong-key", ""} {
		recorder := serve(t, serverWithKey(t, manager.URL, wrongKey), validQuery, slotRequest())

		if recorder.Code != http.StatusBadGateway {
			t.Errorf("key %q: status = %d, want 502 because a rejected key is a configuration fault", wrongKey, recorder.Code)
		}
		if strings.Contains(recorder.Body.String(), "not found") {
			t.Errorf("key %q: the response says %q, which would hide the real problem", wrongKey, recorder.Body.String())
		}
	}
}

func TestAdserve_ARejectedKeyIsNotRemembered(t *testing.T) {
	m := &recordingManager{requireKey: "right"}
	manager := httptest.NewServer(http.HandlerFunc(m.handler))
	defer manager.Close()
	server := serverWithKey(t, manager.URL, "wrong")

	serve(t, server, validQuery, slotRequest())
	serve(t, server, validQuery, slotRequest())

	if len(m.keys) != 2 {
		t.Errorf("the manager was asked %d times over two requests, want 2: a 401 must not enter the known-entity cache", len(m.keys))
	}
}
