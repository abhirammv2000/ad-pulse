package util

import (
	"adserver/cache"
	"log"
	"time"
)

// clock is where the current time comes from. Tests replace it. Flight dates and
// the day and hour targeting rules are all read in UTC.
var clock = time.Now

// dayNumber maps Go weekday names onto the 1-based day numbers used in
// targeting rules (Sunday = 1).
var dayNumber = map[time.Weekday]int{
	time.Sunday:    1,
	time.Monday:    2,
	time.Tuesday:   3,
	time.Wednesday: 4,
	time.Thursday:  5,
	time.Friday:    6,
	time.Saturday:  7,
}

func WithinDuration(startDate, endDate time.Time) bool {
	current := clock().UTC()
	return startDate.Before(current) && endDate.After(current)
}

func GetTime(strTime string) (time.Time, error) {
	return time.Parse(cache.DateLayout, strTime)
}

// AdActive reports whether now falls inside the ad's own flight dates.
func AdActive(ad cache.Ad) bool {
	startDate, endDate, err := ad.Flight()
	if err != nil {
		log.Printf("ad %s has an unparseable %v", ad.AdID, err)
		return false
	}
	return WithinDuration(startDate, endDate)
}

// adInTargetedAdUnit reports whether the ad may serve into this ad unit. An ad
// with no ad-unit list is unrestricted.
func adInTargetedAdUnit(ad cache.Ad, adParam cache.RequestParams) bool {
	if len(ad.AdUnitTargeted) == 0 {
		return true
	}
	return contains(ad.AdUnitTargeted, adParam.AdUnitId)
}

// adInDayTargeting and adInTimeTargeting treat an absent or empty rule as
// "no restriction", so an ad that targets only hours still serves on every day.
func adInDayTargeting(ad cache.Ad) bool {
	if ad.TargetingInfo == nil || len(ad.TargetingInfo.DayTargeting.Values) == 0 {
		return true
	}
	return contains(ad.TargetingInfo.DayTargeting.Values, dayNumber[clock().UTC().Weekday()])
}

func adInTimeTargeting(ad cache.Ad) bool {
	if ad.TargetingInfo == nil || len(ad.TargetingInfo.TimeTargeting.Values) == 0 {
		return true
	}
	return contains(ad.TargetingInfo.TimeTargeting.Values, clock().UTC().Hour())
}

// IsAdAvailable reports whether the ad passes every targeting rule for this request.
func IsAdAvailable(ad cache.Ad, adParam cache.RequestParams) bool {
	return AdActive(ad) &&
		adInTargetedAdUnit(ad, adParam) &&
		adInDayTargeting(ad) &&
		adInTimeTargeting(ad)
}

func contains[T comparable](values []T, target T) bool {
	for _, v := range values {
		if v == target {
			return true
		}
	}
	return false
}
