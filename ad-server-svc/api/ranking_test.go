package api

import (
	"math"
	"testing"

	"adserver/cache"
)

// rankAds takes every ad out of a ranking, best first.
func rankAds(ads []cache.Ad) []cache.Ad {
	candidates := newRanking(ads)
	var ranked []cache.Ad
	for {
		ad, ok := candidates.next()
		if !ok {
			return ranked
		}
		ranked = append(ranked, ad)
	}
}

func pricedAd(id string, priority int, bidType string, bid cache.Money) cache.Ad {
	ad := cache.Ad{AdID: id, AdPriority: priority}
	ad.BidInfo.BidType, ad.BidInfo.Bid = bidType, bid
	return ad
}

func ids(ads []cache.Ad) []string {
	out := make([]string, len(ads))
	for i, ad := range ads {
		out[i] = ad.AdID
	}
	return out
}

func sameOrder(got []cache.Ad, want ...string) bool {
	if len(got) != len(want) {
		return false
	}
	for i := range want {
		if got[i].AdID != want[i] {
			return false
		}
	}
	return true
}

func TestRankAds_PriorityComesFirstWhateverThePrice(t *testing.T) {
	ranked := rankAds([]cache.Ad{
		pricedAd("RICH_BUT_LOW_PRIORITY", 9, "CPM", 100*dollar),
		pricedAd("FIRST", 5, "CPM", dollar),
		pricedAd("MIDDLE", 7, "CPM", 50*dollar),
	})
	if !sameOrder(ranked, "FIRST", "MIDDLE", "RICH_BUT_LOW_PRIORITY") {
		t.Errorf("got %v", ids(ranked))
	}
}

func TestRankAds_WithinAPriorityTheHigherECPMWins(t *testing.T) {
	ranked := rankAds([]cache.Ad{
		pricedAd("CHEAP", 1, "CPM", dollar),
		pricedAd("DEAR", 1, "CPM", 3*dollar),
		pricedAd("UNPRICED", 1, "", 0),
	})
	if !sameOrder(ranked, "DEAR", "CHEAP", "UNPRICED") {
		t.Errorf("got %v", ids(ranked))
	}
}

func TestRankAds_ACPCAdCompetesOnItsExpectedRate(t *testing.T) {
	// A $0.50 CPC ad with a 1% rate earns $5 a thousand impressions, more than a $4 CPM ad.
	cpc := pricedAd("CPC", 1, "CPC", dollar/2)
	cpc.Stats.Clicks, cpc.Stats.Renders = 1_000, 100_000
	ranked := rankAds([]cache.Ad{pricedAd("CPM", 1, "CPM", 4*dollar), cpc})
	if !sameOrder(ranked, "CPC", "CPM") {
		t.Errorf("got %v", ids(ranked))
	}

	// With a 0.5% rate it earns $2.50 and drops behind.
	cpc.Stats.Clicks = 500
	ranked = rankAds([]cache.Ad{pricedAd("CPM", 1, "CPM", 4*dollar), cpc})
	if !sameOrder(ranked, "CPM", "CPC") {
		t.Errorf("got %v", ids(ranked))
	}
}

func TestRankAds_TiesGoToTheLowerIdSoTheOrderNeverChanges(t *testing.T) {
	ranked := rankAds([]cache.Ad{
		pricedAd("B", 1, "CPM", dollar),
		pricedAd("C", 1, "CPM", dollar),
		pricedAd("A", 1, "CPM", dollar),
	})
	if !sameOrder(ranked, "A", "B", "C") {
		t.Errorf("got %v", ids(ranked))
	}
}

func TestRankAds_AHundredAdsComeOutInExactlyTheSortedOrder(t *testing.T) {
	// The heap must give the same order a full sort would, for any mix of priorities, prices and ties.
	var ads []cache.Ad
	for i := 0; i < 100; i++ {
		ads = append(ads, pricedAd(string(rune('A'+i%26))+string(rune('a'+i/26)), i%4, "CPM", cache.Money((i*7919)%5)*dollar))
	}
	ranked := rankAds(ads)
	if len(ranked) != len(ads) {
		t.Fatalf("got %d ads back, want %d", len(ranked), len(ads))
	}
	for i := 1; i < len(ranked); i++ {
		a := rankKey{priority: ranked[i-1].AdPriority, ecpm: ecpm(ranked[i-1]), id: ranked[i-1].AdID}
		b := rankKey{priority: ranked[i].AdPriority, ecpm: ecpm(ranked[i]), id: ranked[i].AdID}
		if better(b, a) {
			t.Fatalf("%s came out before %s, which should win", ranked[i-1].AdID, ranked[i].AdID)
		}
	}
}

func TestRankAds_LeavesTheInputAlone(t *testing.T) {
	ads := []cache.Ad{pricedAd("LATE", 9, "CPM", dollar), pricedAd("EARLY", 1, "CPM", dollar)}
	rankAds(ads)
	if !sameOrder(ads, "LATE", "EARLY") {
		t.Errorf("the input was reordered to %v", ids(ads))
	}
}

func TestExpectedCTR(t *testing.T) {
	cases := []struct {
		name            string
		clicks, renders int64
		want            float64
	}{
		{"a new ad starts at the prior", 0, 0, 0.01},
		{"one click in two renders is not a 50% rate", 1, 2, 2.0 / 102},
		{"a long record is mostly its own rate", 3_000, 100_000, 3_001.0 / 100_100},
	}
	for _, c := range cases {
		if got := expectedCTR(c.clicks, c.renders); math.Abs(got-c.want) > 1e-12 {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
	}
}

func TestECPM(t *testing.T) {
	cpc := pricedAd("CPC", 1, "CPC", dollar)
	cases := []struct {
		name string
		ad   cache.Ad
		want float64
	}{
		{"a CPM ad's eCPM is its bid", pricedAd("CPM", 1, "CPM", 2*dollar), float64((2 * dollar).Nanos())},
		{"a new $1 CPC ad is worth $10 a thousand at the 1% prior", cpc, float64((10 * dollar).Nanos())},
		{"an ad with no bid type is worth nothing", pricedAd("NONE", 1, "", dollar), 0},
	}
	for _, c := range cases {
		if got := ecpm(c.ad); math.Abs(got-c.want) > 1 {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
	}
}
