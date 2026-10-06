package services

import (
	"encoding/base64"
	"net/http"
	"net/url"
	"testing"
)

// This is the same vector ad-server-svc tests against. It was computed with
// Python's hmac module, so a drift between the two Go services shows up as a
// failure in one of them.
const (
	vectorSecret = "test-secret"
	vectorIID    = "eyJhZGlkIjoiQUQxIn0="
	vectorSig    = "092ba8ec55020dcb187ce4b39290b8b08c8fae61f1a7c8b4d14e9dd95982b7ef"
)

func TestSignIIDMatchesTheSharedTestVector(t *testing.T) {
	if got := signIID(vectorSecret, vectorIID); got != vectorSig {
		t.Errorf("signIID = %s, want %s", got, vectorSig)
	}
	// And the vector really is the base64 of {"adid":"AD1"}.
	if raw, _ := base64.StdEncoding.DecodeString(vectorIID); string(raw) != `{"adid":"AD1"}` {
		t.Errorf("vector iid decodes to %q", raw)
	}
}

func TestValidSignature(t *testing.T) {
	cases := []struct {
		name string
		sig  string
		want bool
	}{
		{"correct signature", vectorSig, true},
		{"empty signature", "", false},
		{"wrong signature", "0000000000000000000000000000000000000000000000000000000000000000", false},
		{"truncated signature", vectorSig[:32], false},
		{"upper case is a different string", "092BA8EC55020DCB187CE4B39290B8B08C8FAE61F1A7C8B4D14E9DD95982B7EF", false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := validSignature(vectorSecret, vectorIID, c.sig); got != c.want {
				t.Errorf("validSignature = %v, want %v", got, c.want)
			}
		})
	}
	if validSignature("another-secret", vectorIID, vectorSig) {
		t.Error("a signature made with a different secret was accepted")
	}
}

func signedQuery(secret, iid string) string {
	return "?iid=" + url.QueryEscape(iid) + "&sig=" + signIID(secret, iid)
}

func TestSignedHandlerAcceptsAValidSignature(t *testing.T) {
	publisher := &fakePublisher{}

	recorder := serve(engagementHandler(publisher, "click-topic", vectorSecret), signedQuery(vectorSecret, vectorIID))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", recorder.Code, recorder.Body.String())
	}
	if got := string(publisher.published["click-topic"]); got != `{"adid":"AD1"}` {
		t.Errorf("published %q", got)
	}
}

func TestSignedHandlerRefusesUnsignedAndForgedRequests(t *testing.T) {
	forgedIID := base64.StdEncoding.EncodeToString([]byte(`{"adid":"SOMEONE_ELSES_AD"}`))
	cases := []struct {
		name  string
		query string
	}{
		{"no signature", "?iid=" + vectorIID},
		{"no iid at all", ""},
		{"a signature for a different iid", "?iid=" + url.QueryEscape(forgedIID) + "&sig=" + vectorSig},
		{"a made-up signature", "?iid=" + vectorIID + "&sig=deadbeef"},
		{"signed with the wrong secret", signedQuery("not-the-secret", vectorIID)},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			publisher := &fakePublisher{}

			recorder := serve(engagementHandler(publisher, "click-topic", vectorSecret), c.query)

			if recorder.Code != http.StatusForbidden {
				t.Errorf("status = %d, want 403", recorder.Code)
			}
			if len(publisher.published) != 0 {
				t.Errorf("published %d messages for a request that should have been refused", len(publisher.published))
			}
		})
	}
}

func TestUnsignedModeStillAcceptsPlainUrls(t *testing.T) {
	publisher := &fakePublisher{}

	recorder := serve(engagementHandler(publisher, "click-topic", ""), "?iid="+vectorIID)

	if recorder.Code != http.StatusOK {
		t.Errorf("status = %d, want 200 when no secret is configured", recorder.Code)
	}
}

func TestHandlersReadTheSecretFromTheEnvironment(t *testing.T) {
	t.Setenv("TRACKING_SECRET", vectorSecret)

	if code := serve(ClickServiceHandler(&fakePublisher{}), "?iid="+vectorIID).Code; code != http.StatusForbidden {
		t.Errorf("click handler accepted an unsigned url: status %d", code)
	}
	if code := serve(CSCServiceHandler(&fakePublisher{}), "?iid="+vectorIID).Code; code != http.StatusForbidden {
		t.Errorf("render handler accepted an unsigned url: status %d", code)
	}
	if code := serve(CSCServiceHandler(&fakePublisher{}), signedQuery(vectorSecret, vectorIID)).Code; code != http.StatusOK {
		t.Errorf("render handler refused a signed url: status %d", code)
	}
}
