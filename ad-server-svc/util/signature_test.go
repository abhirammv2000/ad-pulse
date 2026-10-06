package util

import "testing"

// The expected value was computed with Python's hmac module, not with this
// code, and adpulse-engagement-svc tests against the same vector. If the two
// services drift apart, one of the two tests fails.
func TestSignIIDMatchesTheSharedTestVector(t *testing.T) {
	got := SignIID("test-secret", "eyJhZGlkIjoiQUQxIn0=")
	want := "092ba8ec55020dcb187ce4b39290b8b08c8fae61f1a7c8b4d14e9dd95982b7ef"
	if got != want {
		t.Errorf("SignIID = %s, want %s", got, want)
	}
}

func TestSignIIDDependsOnTheSecretAndTheMessage(t *testing.T) {
	base := SignIID("secret-a", "payload")
	if base == SignIID("secret-b", "payload") {
		t.Error("two secrets gave the same signature")
	}
	if base == SignIID("secret-a", "payload2") {
		t.Error("two payloads gave the same signature")
	}
	if len(base) != 64 {
		t.Errorf("signature length = %d, want 64 hex characters", len(base))
	}
}
