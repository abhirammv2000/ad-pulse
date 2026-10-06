package services

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
)

// signIID returns the hex HMAC-SHA256 of an encoded impression id. It has to
// match SignIID in ad-server-svc, which signs the URLs this service receives.
func signIID(secret, encodedIID string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(encodedIID))
	return hex.EncodeToString(mac.Sum(nil))
}

// validSignature reports whether sig is the right signature for the encoded iid.
// The comparison takes the same time whatever the input, so a caller can't
// guess a signature one character at a time.
func validSignature(secret, encodedIID, sig string) bool {
	return hmac.Equal([]byte(signIID(secret, encodedIID)), []byte(sig))
}
