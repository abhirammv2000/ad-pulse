package util

import (
	"testing"
	"time"

	"adserver/cache"
)

func fmtTime(t time.Time) string {
	return t.UTC().Format(timeLayout)
}

func TestWithinDuration(t *testing.T) {
	now := time.Now().UTC()

	cases := []struct {
		name  string
		start time.Time
		end   time.Time
		want  bool
	}{
		{"now is inside the window", now.Add(-time.Hour), now.Add(time.Hour), true},
		{"window hasn't started yet", now.Add(time.Hour), now.Add(2 * time.Hour), false},
		{"window already ended", now.Add(-2 * time.Hour), now.Add(-time.Hour), false},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := WithinDuration(c.start, c.end); got != c.want {
				t.Errorf("WithinDuration(%v, %v) = %v, want %v", c.start, c.end, got, c.want)
			}
		})
	}
}

func TestGetTime(t *testing.T) {
	if _, err := GetTime("2026-09-17T13:00:00"); err != nil {
		t.Errorf("expected a valid timeLayout string to parse, got error: %v", err)
	}
	if _, err := GetTime("not-a-date"); err == nil {
		t.Error("expected an error parsing a non-date string, got nil")
	}
}

func TestAdActive(t *testing.T) {
	now := time.Now().UTC()
	validAd := cache.Ad{
		AdID:      "AD1",
		StartDate: fmtTime(now.Add(-time.Hour)),
		EndDate:   fmtTime(now.Add(time.Hour)),
	}
	expiredAd := cache.Ad{
		AdID:      "AD2",
		StartDate: fmtTime(now.Add(-2 * time.Hour)),
		EndDate:   fmtTime(now.Add(-time.Hour)),
	}
	malformedAd := cache.Ad{
		AdID:      "AD3",
		StartDate: "not-a-date",
		EndDate:   fmtTime(now.Add(time.Hour)),
	}

	if !AdActive(validAd) {
		t.Error("expected an ad within its flight dates to be active")
	}
	if AdActive(expiredAd) {
		t.Error("expected an ad past its end date to be inactive")
	}
	if AdActive(malformedAd) {
		t.Error("expected an ad with an unparseable start date to be treated as inactive, not to panic or error out")
	}
}

func TestIsAdAvailable_AdUnitTargeting(t *testing.T) {
	now := time.Now().UTC()
	base := cache.Ad{
		AdID:      "AD1",
		StartDate: fmtTime(now.Add(-time.Hour)),
		EndDate:   fmtTime(now.Add(time.Hour)),
	}

	unrestricted := base
	unrestricted.AdUnitTargeted = nil
	if !IsAdAvailable(unrestricted, cache.RequestParams{AdUnitId: "ADU1"}) {
		t.Error("expected an ad with no ad-unit targeting to be available for any ad unit")
	}

	targeted := base
	targeted.AdUnitTargeted = []string{"ADU1", "ADU2"}
	if !IsAdAvailable(targeted, cache.RequestParams{AdUnitId: "ADU2"}) {
		t.Error("expected an ad to be available for an ad unit in its targeting list")
	}
	if IsAdAvailable(targeted, cache.RequestParams{AdUnitId: "ADU3"}) {
		t.Error("expected an ad to NOT be available for an ad unit outside its targeting list")
	}
}

func TestIsAdAvailable_ExpiredAdIsNeverAvailable(t *testing.T) {
	now := time.Now().UTC()
	expired := cache.Ad{
		AdID:      "AD1",
		StartDate: fmtTime(now.Add(-2 * time.Hour)),
		EndDate:   fmtTime(now.Add(-time.Hour)),
	}
	if IsAdAvailable(expired, cache.RequestParams{AdUnitId: "ADU1"}) {
		t.Error("expected an expired ad to be unavailable regardless of targeting")
	}
}

func TestRankAds(t *testing.T) {
	ads := []cache.Ad{
		{AdID: "low-priority-number-wins", AdPriority: 5},
		{AdID: "highest-priority-number", AdPriority: 9},
		{AdID: "middle", AdPriority: 7},
	}

	ranked := RankAds(ads)

	if ranked[0].AdID != "low-priority-number-wins" || ranked[1].AdID != "middle" || ranked[2].AdID != "highest-priority-number" {
		t.Errorf("expected ads ranked by ascending AdPriority (lowest number first), got order: %s, %s, %s",
			ranked[0].AdID, ranked[1].AdID, ranked[2].AdID)
	}
}
