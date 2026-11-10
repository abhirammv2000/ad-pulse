package api

import (
	"errors"
	"net/http"
	"testing"
	"time"

	"adserver/cache"
)

const dollar = cache.Money(1_000_000)

func TestBlockedBy(t *testing.T) {
	noon := 12 * time.Hour
	ten := (10 * dollar).Nanos()
	cases := []struct {
		name          string
		l             limits
		total, today  int64
		sinceMidnight time.Duration
		want          string
	}{
		{"no budget at all", limits{}, ten * 100, ten * 100, noon, ""},
		{"under the total", limits{total: 10 * dollar}, ten - 1, 0, noon, ""},
		{"the total is reached exactly", limits{total: 10 * dollar}, ten, 0, noon, reasonTotalBudget},
		{"the daily budget is reached", limits{daily: 10 * dollar}, 0, ten, 23 * time.Hour, reasonDailyBudget},
		// At noon an even pace has spent half the day's budget, and the headroom adds an hour more: 13/24.
		{"on pace at noon", limits{daily: 10 * dollar}, 0, ten * 13 / 24, noon, ""},
		{"ahead of pace at noon", limits{daily: 10 * dollar}, 0, ten*13/24 + 1, noon, reasonPacing},
		{"the first hour can spend an hour's worth", limits{daily: 24 * dollar}, 0, dollar.Nanos(), 0, ""},
		{"in the last hour only the daily budget limits", limits{daily: 10 * dollar}, 0, ten - 1, 23*time.Hour + 30*time.Minute, ""},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := blockedBy(c.l, c.total, c.today, c.sinceMidnight); got != c.want {
				t.Errorf("got %q, want %q", got, c.want)
			}
		})
	}
}

func TestPriceNanos(t *testing.T) {
	cases := []struct {
		bidType string
		bid     cache.Money
		want    int64
	}{
		{"CPM", 1 * dollar, 1_000_000},   // one render of a $1 CPM costs $0.001
		{"CPM", 1_500, 1_500},            // $0.0015 CPM: 1.5 micros a render, a whole number of nanos
		{"CPC", dollar / 4, 250_000_000}, // a click costs the whole bid
		{"", 1 * dollar, 0},              // no bid type, no charge
		{"CPD", 1 * dollar, 0},           // not supported, so never charged
	}
	for _, c := range cases {
		ad := cache.Ad{}
		ad.BidInfo.BidType, ad.BidInfo.Bid = c.bidType, c.bid
		if got := priceNanos(ad); got != c.want {
			t.Errorf("%s %s: got %d nanos, want %d", c.bidType, c.bid, got, c.want)
		}
	}
}

// budgetTestTime is when these tests serve, so the spend keys and the pace are known.
var budgetTestTime = time.Date(2026, 11, 8, 12, 0, 0, 0, time.UTC)

func budgetServer(t *testing.T, store *fakeStore) *Server {
	t.Helper()
	server := newTestServer(t, store, adManager(t).URL)
	server.now = func() time.Time { return budgetTestTime }
	return server
}

func budgetedAd(id string, priority int, total cache.Money) cache.Ad {
	ad := liveAd(id, priority)
	ad.Budget.TotalBudget = total
	return ad
}

func servedAds(t *testing.T, server *Server) []string {
	t.Helper()
	recorder := serve(t, server, validQuery, cache.RequestBody{
		ID:  "req1",
		Imp: []cache.Impression{impression("imp1", 300, 250), impression("imp2", 300, 250)},
	})
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

func TestAdserve_AnAdThatHasSpentItsBudgetIsNotServed(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, budgetedAd("SPENT", 1, 10*dollar), budgetedAd("ROOM", 2, 10*dollar))
	store.values["spend:ad:SPENT"] = "10000000000" // exactly $10 in nanos
	store.values["spend:ad:ROOM"] = "9999999999"

	got := servedAds(t, budgetServer(t, store))

	if len(got) != 1 || got[0] != "ROOM" {
		t.Errorf("served %v, want only ROOM", got)
	}
}

func TestAdserve_ACampaignThatHasSpentItsBudgetStopsAllItsAds(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1), liveAd("AD2", 2))
	start, end := window(-time.Hour, time.Hour)
	campaign := cache.Campaign{CampaignID: "C1", StartDate: start, EndDate: end}
	campaign.Budget.TotalBudget = 5 * dollar
	store.values["campaigns"] = mustJSON(t, []cache.Campaign{campaign})
	store.values["spend:campaign:C1"] = "5000000000"

	if got := servedAds(t, budgetServer(t, store)); got != nil {
		t.Errorf("served %v, want nothing", got)
	}
}

func TestAdserve_OnlyTodaysSpendCountsAgainstTheDailyBudget(t *testing.T) {
	store := newFakeStore()
	ad := liveAd("AD1", 1)
	ad.Budget.DailyBudget = 10 * dollar
	seedCampaign(t, store, ad)
	server := budgetServer(t, store)

	store.values["spend:ad:AD1:2026-11-07"] = "10000000000" // yesterday's budget, all spent
	if got := servedAds(t, server); len(got) != 1 {
		t.Fatalf("served %v, want AD1: yesterday's spend should not count today", got)
	}

	store.values["spend:ad:AD1:2026-11-08"] = "10000000000"
	if got := servedAds(t, server); got != nil {
		t.Errorf("served %v, want nothing once today's budget is spent", got)
	}
}

func TestAdserve_AnAdAheadOfPaceWaits(t *testing.T) {
	store := newFakeStore()
	ad := liveAd("AD1", 1)
	ad.Budget.DailyBudget = 24 * dollar
	seedCampaign(t, store, ad)
	// At noon, with an hour of headroom, the pace allows 13 of the 24 dollars.
	store.values["spend:ad:AD1:2026-11-08"] = "14000000000"

	if got := servedAds(t, budgetServer(t, store)); got != nil {
		t.Errorf("served %v, want nothing while ahead of pace", got)
	}
}

func TestAdserve_ReadsAllSpendInOneRoundTrip(t *testing.T) {
	store := newFakeStore()
	var ads []cache.Ad
	for _, id := range []string{"A", "B", "C", "D", "E"} {
		ads = append(ads, budgetedAd(id, 1, 10*dollar))
	}
	seedCampaign(t, store, ads...)

	servedAds(t, budgetServer(t, store))

	if store.mgetCalls != 1 {
		t.Errorf("read spend %d times for five budgeted ads, want once", store.mgetCalls)
	}
}

func TestAdserve_AdsWithoutBudgetsCostNoSpendRead(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1), liveAd("AD2", 2))

	servedAds(t, budgetServer(t, store))

	if store.mgetCalls != 0 {
		t.Errorf("read spend %d times with no budgets anywhere, want 0", store.mgetCalls)
	}
}

func TestAdserve_UnreadableSpendStopsOnlyThatAd(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, budgetedAd("BROKEN", 1, 10*dollar), budgetedAd("FINE", 2, 10*dollar))
	store.values["spend:ad:BROKEN"] = "not a number"

	got := servedAds(t, budgetServer(t, store))

	if len(got) != 1 || got[0] != "FINE" {
		t.Errorf("served %v, want only FINE", got)
	}
}

func TestAdserve_ASpendReadFailureIsA500(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, budgetedAd("AD1", 1, 10*dollar))
	store.mgetErr = errors.New("redis is down")

	if code := serve(t, budgetServer(t, store), validQuery, slotRequest()).Code; code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", code)
	}
}

func TestAdserve_TheIidCarriesThePriceOfTheBillableEvent(t *testing.T) {
	store := newFakeStore()
	ad := liveAd("AD1", 1)
	ad.BidInfo.BidType, ad.BidInfo.Bid = "CPC", dollar/2
	seedCampaign(t, store, ad)

	bid := decodeResponse(t, serve(t, budgetServer(t, store), validQuery, slotRequest())).Bid[0]

	for _, url := range []string{bid.Ext.ClickUrl, bid.Ext.RenderUrl} {
		iid := iidFrom(t, url)
		if iid.BidType != "CPC" || iid.PriceNanos != 500_000_000 {
			t.Errorf("iid carries %s at %d nanos, want CPC at 500000000", iid.BidType, iid.PriceNanos)
		}
	}
}
