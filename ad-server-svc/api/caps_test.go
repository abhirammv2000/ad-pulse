package api

import (
	"errors"
	"net/http"
	"reflect"
	"strings"
	"testing"
	"time"

	"adserver/cache"
)

// freqCap builds a frequency cap, such as freqCap("AD", "CSC", 2, "HOUR", 1) for two renders of the ad an hour.
func freqCap(entity, event string, maxCount int, unit string, value int) cache.FrequencyCap {
	c := cache.FrequencyCap{UserCap: true, EntityType: entity, EventType: event}
	c.TimeFrame.MaxCount, c.TimeFrame.TimeWindowType, c.TimeFrame.Value = maxCount, unit, value
	return c
}

func cappedAd(id string, priority int, caps ...cache.FrequencyCap) cache.Ad {
	ad := liveAd(id, priority)
	ad.FrequencyCaps.FrequencyCapList = caps
	return ad
}

// requestFor asks for two 300x250 slots on behalf of a user.
func requestFor(userID string) cache.RequestBody {
	body := cache.RequestBody{ID: "req1", Imp: []cache.Impression{impression("imp1", 300, 250), impression("imp2", 300, 250)}}
	body.User.ID = userID
	return body
}

func servedTo(t *testing.T, server *Server, userID string) []string {
	t.Helper()
	recorder := serve(t, server, validQuery, requestFor(userID))
	if recorder.Code == http.StatusNoContent {
		return nil
	}
	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", recorder.Code, recorder.Body.String())
	}
	var ids []string
	for _, bid := range decodeResponse(t, recorder).Bid {
		ids = append(ids, bid.AdID)
	}
	return ids
}

// testNow is the fixed serve time of these tests, in Unix seconds.
var testNow = budgetTestTime.Unix()

func TestAdserve_AUserWhoHasReachedACapDoesNotGetTheAd(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, cappedAd("CAPPED", 1, freqCap("AD", "CSC", 2, "HOUR", 1)))
	store.addEvent("fc:AD:CAPPED:CSC:alice", "bid1", testNow-100)
	store.addEvent("fc:AD:CAPPED:CSC:alice", "bid2", testNow-50)
	server := budgetServer(t, store)

	if got := servedTo(t, server, "alice"); got != nil {
		t.Errorf("alice got %v after two renders this hour, want nothing", got)
	}
	if got := servedTo(t, server, "bob"); len(got) != 1 || got[0] != "CAPPED" {
		t.Errorf("bob got %v, want CAPPED: the cap is per user", got)
	}
}

func TestAdserve_OnlyEventsInsideTheWindowCount(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, cappedAd("AD1", 1, freqCap("AD", "CSC", 1, "HOUR", 1)))
	server := budgetServer(t, store)

	// Exactly one hour ago is outside a one hour window.
	store.addEvent("fc:AD:AD1:CSC:alice", "old", testNow-3600)
	if got := servedTo(t, server, "alice"); len(got) != 1 {
		t.Fatalf("got %v, want AD1: the only render is an hour old", got)
	}

	store.addEvent("fc:AD:AD1:CSC:alice", "recent", testNow-3599)
	if got := servedTo(t, server, "alice"); got != nil {
		t.Errorf("got %v, want nothing once a render falls inside the hour", got)
	}
}

func TestAdserve_ClicksAndRendersAreCountedSeparately(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, cappedAd("AD1", 1, freqCap("AD", "CLK", 1, "DAY", 1)))
	store.addEvent("fc:AD:AD1:CSC:alice", "bid1", testNow-10) // a render, which this click cap ignores

	if got := servedTo(t, budgetServer(t, store), "alice"); len(got) != 1 {
		t.Errorf("got %v, want AD1: a render does not count against a click cap", got)
	}
}

func TestAdserve_ACampaignWideCapCountsEveryAdOfTheCampaign(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store,
		cappedAd("AD1", 1, freqCap("CAMPAIGN", "CSC", 1, "DAY", 1)),
		cappedAd("AD2", 2, freqCap("CAMPAIGN", "CSC", 1, "DAY", 1)),
	)
	store.addEvent("fc:CAMPAIGN:C1:CSC:alice", "bid-of-AD2", testNow-10)

	if got := servedTo(t, budgetServer(t, store), "alice"); got != nil {
		t.Errorf("got %v, want nothing: alice already saw an ad of C1 today", got)
	}
}

func TestAdserve_ACapOnTheCampaignAppliesToItsAds(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1), liveAd("AD2", 2))
	start, end := window(-time.Hour, time.Hour)
	campaign := cache.Campaign{CampaignID: "C1", StartDate: start, EndDate: end}
	// An AD cap set on the campaign limits each of its ads on its own.
	campaign.FrequencyCaps.FrequencyCapList = []cache.FrequencyCap{freqCap("AD", "CSC", 1, "DAY", 1)}
	store.values["campaigns"] = mustJSON(t, []cache.Campaign{campaign})
	store.addEvent("fc:AD:AD1:CSC:alice", "bid1", testNow-10)

	if got := servedTo(t, budgetServer(t, store), "alice"); len(got) != 1 || got[0] != "AD2" {
		t.Errorf("got %v, want only AD2", got)
	}
}

func TestAdserve_ACappedAdNeedsAUserID(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, cappedAd("CAPPED", 1, freqCap("AD", "CSC", 3, "DAY", 1)), liveAd("OPEN", 2))
	server := budgetServer(t, store)

	if got := servedTo(t, server, ""); len(got) != 1 || got[0] != "OPEN" {
		t.Errorf("with no user id got %v, want only OPEN", got)
	}
	if got := servedTo(t, server, strings.Repeat("u", maxUserIDLength+1)); len(got) != 1 || got[0] != "OPEN" {
		t.Errorf("with an over-long user id got %v, want only OPEN", got)
	}
}

func TestAdserve_ACapTheServerCannotApplyStopsOnlyItsAd(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, cappedAd("ODD", 1, freqCap("AD", "CSC", 3, "FORTNIGHT", 1)), liveAd("FINE", 2))

	if got := servedTo(t, budgetServer(t, store), "alice"); len(got) != 1 || got[0] != "FINE" {
		t.Errorf("got %v, want only FINE", got)
	}
}

func TestAdserve_CountsEveryCapInOneRoundTripAndNoneWithoutCaps(t *testing.T) {
	store := newFakeStore()
	var ads []cache.Ad
	for _, id := range []string{"A", "B", "C", "D"} {
		ads = append(ads, cappedAd(id, 1, freqCap("AD", "CSC", 3, "DAY", 1), freqCap("CAMPAIGN", "CLK", 1, "WEEK", 1)))
	}
	seedCampaign(t, store, ads...)
	servedTo(t, budgetServer(t, store), "alice")
	if store.countCalls != 1 {
		t.Errorf("counted events %d times for four capped ads, want once", store.countCalls)
	}

	plain := newFakeStore()
	seedCampaign(t, plain, liveAd("AD1", 1))
	servedTo(t, budgetServer(t, plain), "alice")
	if plain.countCalls != 0 {
		t.Errorf("counted events %d times with no caps anywhere, want 0", plain.countCalls)
	}
}

func TestAdserve_ACountFailureIsA500(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, cappedAd("AD1", 1, freqCap("AD", "CSC", 3, "DAY", 1)))
	store.countErr = errors.New("redis is down")

	if code := serve(t, budgetServer(t, store), validQuery, requestFor("alice")).Code; code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", code)
	}
}

func TestAdserve_OnlyACappedAdsUrlsCarryTheUserAndItsCounters(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store,
		cappedAd("CAPPED", 1, freqCap("AD", "CSC", 3, "DAY", 1), freqCap("CAMPAIGN", "CLK", 1, "WEEK", 1)),
		liveAd("OPEN", 2),
	)

	recorder := serve(t, budgetServer(t, store), validQuery, requestFor("alice"))
	bids := decodeResponse(t, recorder).Bid
	if len(bids) != 2 {
		t.Fatalf("got %d bids, want 2", len(bids))
	}
	for _, bid := range bids {
		iid := iidFrom(t, bid.Ext.RenderUrl)
		switch bid.AdID {
		case "CAPPED":
			if iid.UserID != "alice" || !reflect.DeepEqual(iid.Counters, []string{"AD:CSC", "CAMPAIGN:CLK"}) {
				t.Errorf("capped ad's iid has user %q and counters %v", iid.UserID, iid.Counters)
			}
		case "OPEN":
			if iid.UserID != "" || iid.Counters != nil {
				t.Errorf("an uncapped ad's iid carries user %q and counters %v", iid.UserID, iid.Counters)
			}
		}
	}
}

func TestAdserve_TheServeTimeAndTheCapWindowsUseOneClock(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))

	bid := decodeResponse(t, serve(t, budgetServer(t, store), validQuery, slotRequest())).Bid[0]

	if got := iidFrom(t, bid.Ext.RenderUrl).RequestTimeStamp; got != testNow {
		t.Errorf("serve time %d, want the server's clock %d", got, testNow)
	}
}

func TestCountersFor(t *testing.T) {
	got := countersFor([]cache.FrequencyCap{
		freqCap("CAMPAIGN", "CSC", 1, "DAY", 1),
		freqCap("AD", "CLK", 1, "DAY", 1),
		freqCap("AD", "CLK", 5, "WEEK", 1),
	})
	if want := []string{"AD:CLK", "CAMPAIGN:CSC"}; !reflect.DeepEqual(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}
