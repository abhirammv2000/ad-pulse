package api

import (
	"encoding/json"
	"sync"
	"sync/atomic"
)

// contentCache remembers the result of decoding a JSON string, keyed by the string itself.
//
// An ad request decodes every campaign and every ad it looks at, and the same strings come back from Redis on
// every request until the refresh service changes them. Decoding was most of the CPU time of a request (see the
// profile in the README), so a string that was already decoded is not decoded again.
//
// Keying by the text, and not by an id or a timestamp, is what makes this safe: the decoded value is a pure
// function of the text, so it can never be out of date. When an ad changes in Redis its text changes and it
// simply misses.
//
// Memory is bounded with two generations. New entries go into current. When current reaches limit it becomes
// previous and a fresh current starts, so an entry that is still being used survives the swap (a hit in previous
// is copied into current) and one that is not used for a whole generation is dropped. At most 2 x limit entries
// are held.
//
// The values are shared between requests. A struct is copied on return, but slices and pointers inside it are not,
// so callers must treat them as read-only. The serve path only reads them.
type contentCache[T any] struct {
	mu       sync.Mutex
	limit    int
	current  map[string]T
	previous map[string]T

	hits, misses atomic.Uint64
}

func newContentCache[T any](limit int) *contentCache[T] {
	if limit < 1 {
		limit = 1
	}
	return &contentCache[T]{limit: limit, current: make(map[string]T), previous: make(map[string]T)}
}

// get returns the decoded value for raw. A string that does not decode is an error every time and is not stored.
func (c *contentCache[T]) get(raw string) (T, error) {
	c.mu.Lock()
	if value, ok := c.current[raw]; ok {
		c.mu.Unlock()
		c.hits.Add(1)
		return value, nil
	}
	if value, ok := c.previous[raw]; ok {
		c.store(raw, value)
		c.mu.Unlock()
		c.hits.Add(1)
		return value, nil
	}
	c.mu.Unlock()

	// Decode outside the lock, so one slow decode does not hold up every other request.
	var value T
	if err := json.Unmarshal([]byte(raw), &value); err != nil {
		var zero T
		return zero, err
	}
	c.misses.Add(1)

	c.mu.Lock()
	c.store(raw, value)
	c.mu.Unlock()
	return value, nil
}

// store adds an entry to the current generation, starting a new one when it is full. The caller holds mu.
func (c *contentCache[T]) store(raw string, value T) {
	if len(c.current) >= c.limit {
		c.previous = c.current
		c.current = make(map[string]T, c.limit)
	}
	c.current[raw] = value
}

// size is how many entries are held, for tests.
func (c *contentCache[T]) size() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return len(c.current) + len(c.previous)
}
