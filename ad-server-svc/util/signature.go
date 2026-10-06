package util

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
)

// SignIID returns the hex HMAC-SHA256 of an encoded impression id.
//
// The ad server puts this in the `sig` parameter of every click and render URL,
// and adpulse-engagement-svc recomputes it before counting the event. Without
// it anyone could build an `iid` for any ad. Both services must sign the
// base64 text exactly as it appears in the URL.
func SignIID(secret, encodedIID string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(encodedIID))
	return hex.EncodeToString(mac.Sum(nil))
}
