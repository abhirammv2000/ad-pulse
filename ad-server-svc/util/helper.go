package util

import (
	"adserver/cache"
	"fmt"
	"log"
	"sort"
	"time"
)

var dayNumber map[string]int = map[string]int{
	"Sunday":    1,
	"Monday":    2,
	"Tuesday":   3,
	"Wednesday": 4,
	"Thursday":  5,
	"Friday":    6,
	"Saturday":  7,
}

func WithinDuration(startDate, endDate time.Time) bool {
	currentTime := time.Now().UTC()
	if startDate.Before(currentTime) && endDate.After(currentTime) {
		return true
	}
	return false
}

func GetTime(strTime string) (time.Time, error) {
	layout := "2006-01-02T15:04:05"
	timeInTimeFormat, err := time.Parse(layout, strTime)
	if err != nil {
		return time.Time{}, err
	}
	return timeInTimeFormat, nil
}

func AdActive(ad cache.Ad) bool {
	startDate, err := GetTime(ad.StartDate)
	if err != nil {
		log.Println(err.Error())
		return false
	}
	endDate, err := GetTime(ad.EndDate)
	if err != nil {
		log.Println(err.Error())
		return false
	}
	if WithinDuration(startDate, endDate) {
		return true
	}
	return false
}

func adInTargettedAdUnit(ad cache.Ad, adParam cache.RequestParams) bool {
	adUnitFlag := false
	for _, adUnit := range ad.AdUnitTargeted {
		if adUnit == adParam.AdUnitId {
			adUnitFlag = true
			break
		}
	}
	if ad.AdUnitTargeted == nil {
		adUnitFlag = true
	}
	return adUnitFlag
}

func adInDayTargeting(ad cache.Ad) bool {
	dayTargetingFlag := false
	dayOfTheWeek := dayNumber[time.Now().Weekday().String()]
	if ad.TargetingInfo == nil {
		return true
	}
	fmt.Println("day of the week: ", dayOfTheWeek, ad.TargetingInfo.DayTargeting.Values)
	for _, dayNumber := range ad.TargetingInfo.DayTargeting.Values {
		if dayNumber == dayOfTheWeek {
			dayTargetingFlag = true
			break
		}
	}

	return dayTargetingFlag
}

func adInTimeTargeting(ad cache.Ad) bool {
	timeTargetingFlag := false
	hourOfTheDay := time.Now().Hour()
	if ad.TargetingInfo == nil {
		return true
	}
	fmt.Println("hour of the day: ", hourOfTheDay, ad.TargetingInfo.TimeTargeting.Values)
	for _, hour := range ad.TargetingInfo.TimeTargeting.Values {
		if hour == hourOfTheDay {
			timeTargetingFlag = true
			break
		}
	}
	return timeTargetingFlag
}

func IsAdAvailable(ad cache.Ad, adParam cache.RequestParams, adBody cache.RequestBody) (bool, error) {
	if !AdActive(ad) {
		return false, nil
	}
	if !adInTargettedAdUnit(ad, adParam) {
		return false, nil
	}
	if !adInDayTargeting(ad) {
		return false, nil
	}
	if !adInTimeTargeting(ad) {
		return false, nil
	}
	return true, nil
}

func RankAds(ads []cache.Ad) []cache.Ad {
	sort.Slice(ads, func(i, j int) bool {
		return ads[i].AdPriority < ads[j].AdPriority
	})
	return ads
}
