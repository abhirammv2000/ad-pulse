package cache

import (
	"encoding/json"
	"fmt"
	"time"
)

// DateLayout is the format the ad manager writes dates in. Python's isoformat()
// adds microseconds when a date has them, and time.Parse accepts those too.
const DateLayout = "2006-01-02T15:04:05"

// flight is an ad's start and end, parsed once when the ad is decoded. The decoded
// ad is shared between requests and this is never changed, so it is safe to share.
type flight struct {
	start, end time.Time
	err        error
}

func parseFlight(start, end string) *flight {
	startDate, err := time.Parse(DateLayout, start)
	if err != nil {
		return &flight{err: fmt.Errorf("start date: %w", err)}
	}
	endDate, err := time.Parse(DateLayout, end)
	if err != nil {
		return &flight{err: fmt.Errorf("end date: %w", err)}
	}
	return &flight{start: startDate, end: endDate}
}

// UnmarshalJSON decodes an ad and parses its flight dates. Every request used to
// parse the dates of every ad again, and that was a large share of a request's CPU.
func (ad *Ad) UnmarshalJSON(data []byte) error {
	type plain Ad // the same fields without this method, so decoding does not call itself
	if err := json.Unmarshal(data, (*plain)(ad)); err != nil {
		return err
	}
	ad.flight = parseFlight(ad.StartDate, ad.EndDate)
	return nil
}

// Flight returns the ad's start and end. An ad that was not decoded from JSON, as in
// tests, has its dates parsed here instead.
func (ad Ad) Flight() (start, end time.Time, err error) {
	f := ad.flight
	if f == nil {
		f = parseFlight(ad.StartDate, ad.EndDate)
	}
	return f.start, f.end, f.err
}
