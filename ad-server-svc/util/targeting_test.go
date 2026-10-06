package util

import (
	"testing"
	"time"

	"adserver/cache"
)

// freezeClock makes util think it is `at` until the test ends.
func freezeClock(t *testing.T, at time.Time) {
	t.Helper()
	original := clock
	clock = func() time.Time { return at }
	t.Cleanup(func() { clock = original })
}

func adWithTargeting(days, hours []int) cache.Ad {
	ad := cache.Ad{
		AdID:      "AD1",
		StartDate: "2020-01-01T00:00:00",
		EndDate:   "2099-01-01T00:00:00",
	}
	ad.TargetingInfo = &cache.TargetingInfo{
		DayTargeting:  cache.DayTargeting{Values: days},
		TimeTargeting: cache.TimeTargeting{Values: hours},
	}
	return ad
}

func TestDayTargeting(t *testing.T) {
	// 2026-09-23 is a Wednesday, which is day 4 when Sunday is 1.
	freezeClock(t, time.Date(2026, 9, 23, 10, 0, 0, 0, time.UTC))
	params := cache.RequestParams{AdUnitId: "ADU1"}

	cases := []struct {
		name string
		days []int
		want bool
	}{
		{"no day rule means every day", nil, true},
		{"today is in the list", []int{2, 4, 6}, true},
		{"today is not in the list", []int{1, 7}, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := IsAdAvailable(adWithTargeting(c.days, nil), params); got != c.want {
				t.Errorf("IsAdAvailable = %v, want %v", got, c.want)
			}
		})
	}
}

func TestDayNumbersRunFromSundayToSaturday(t *testing.T) {
	params := cache.RequestParams{AdUnitId: "ADU1"}
	// 2026-09-20 is a Sunday.
	for offset, weekday := range []int{1, 2, 3, 4, 5, 6, 7} {
		freezeClock(t, time.Date(2026, 9, 20+offset, 12, 0, 0, 0, time.UTC))
		if !IsAdAvailable(adWithTargeting([]int{weekday}, nil), params) {
			t.Errorf("day %d should match %s", weekday, clock().Weekday())
		}
	}
}

func TestHourTargeting(t *testing.T) {
	freezeClock(t, time.Date(2026, 9, 23, 14, 30, 0, 0, time.UTC))
	params := cache.RequestParams{AdUnitId: "ADU1"}

	cases := []struct {
		name  string
		hours []int
		want  bool
	}{
		{"no hour rule means every hour", nil, true},
		{"this hour is in the list", []int{9, 14, 20}, true},
		{"this hour is not in the list", []int{0, 1, 2}, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := IsAdAvailable(adWithTargeting(nil, c.hours), params); got != c.want {
				t.Errorf("IsAdAvailable = %v, want %v", got, c.want)
			}
		})
	}
}

func TestAnAdWithNoTargetingInfoIsUnrestricted(t *testing.T) {
	freezeClock(t, time.Date(2026, 9, 23, 3, 0, 0, 0, time.UTC))
	ad := cache.Ad{AdID: "AD1", StartDate: "2020-01-01T00:00:00", EndDate: "2099-01-01T00:00:00"}

	if !IsAdAvailable(ad, cache.RequestParams{AdUnitId: "ADU1"}) {
		t.Error("an ad with no targeting info should serve at any time")
	}
}

func TestTargetingReadsTheClockInUTCWhateverTheMachineZone(t *testing.T) {
	// 23:30 on Wednesday in UTC+10 is 13:30 on Wednesday UTC.
	plusTen := time.FixedZone("UTC+10", 10*60*60)
	freezeClock(t, time.Date(2026, 9, 23, 23, 30, 0, 0, plusTen))
	params := cache.RequestParams{AdUnitId: "ADU1"}

	if !IsAdAvailable(adWithTargeting(nil, []int{13}), params) {
		t.Error("hour 13 (UTC) should match")
	}
	if IsAdAvailable(adWithTargeting(nil, []int{23}), params) {
		t.Error("hour 23 is the local hour, not the UTC hour, so it should not match")
	}

	// 02:00 Thursday in UTC+10 is still Wednesday 16:00 UTC the day before.
	freezeClock(t, time.Date(2026, 9, 24, 2, 0, 0, 0, plusTen))
	if !IsAdAvailable(adWithTargeting([]int{4}, nil), params) {
		t.Error("the UTC day is still Wednesday (4)")
	}
}

func TestWithinDurationUsesTheClock(t *testing.T) {
	freezeClock(t, time.Date(2026, 9, 23, 12, 0, 0, 0, time.UTC))
	start := time.Date(2026, 9, 23, 0, 0, 0, 0, time.UTC)
	end := time.Date(2026, 9, 24, 0, 0, 0, 0, time.UTC)

	if !WithinDuration(start, end) {
		t.Error("noon is inside the day")
	}
	freezeClock(t, time.Date(2026, 9, 24, 0, 0, 1, 0, time.UTC))
	if WithinDuration(start, end) {
		t.Error("just after midnight is outside the window")
	}
}
