package api

import (
	"sync"
	"time"
)

// knownEntityTTL is how long a publisher or ad unit that the manager confirmed
// is remembered. A deleted one can still be served for up to this long.
const knownEntityTTL = 30 * time.Second

// knownEntities remembers lookups the ad manager answered with 200, so most ad
// requests skip those two round trips. Misses and errors are never stored: an
// unknown id is re-checked every time, which is how a newly created publisher
// starts working at once.
type knownEntities struct {
	mu      sync.Mutex
	now     func() time.Time
	expires map[string]time.Time
}

func newKnownEntities() *knownEntities {
	return &knownEntities{now: time.Now, expires: make(map[string]time.Time)}
}

// has reports whether path was confirmed within the TTL.
func (k *knownEntities) has(path string) bool {
	k.mu.Lock()
	defer k.mu.Unlock()

	expiry, ok := k.expires[path]
	if !ok {
		return false
	}
	if !k.now().Before(expiry) {
		delete(k.expires, path)
		return false
	}
	return true
}

// remember stores a confirmed path.
func (k *knownEntities) remember(path string) {
	k.mu.Lock()
	defer k.mu.Unlock()

	// Drop expired entries now and then so the map can't grow without bound
	// when callers send many different ids.
	if len(k.expires) > 1000 {
		now := k.now()
		for key, expiry := range k.expires {
			if !now.Before(expiry) {
				delete(k.expires, key)
			}
		}
	}
	k.expires[path] = k.now().Add(knownEntityTTL)
}
