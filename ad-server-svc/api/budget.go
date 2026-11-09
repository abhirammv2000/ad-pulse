package api

import (
	"fmt"
	"log"
	"strconv"
	"time"

	"adserver/cache"
)

// Budgets and pacing.
//
// adpulse-engagement-subscriber-svc adds the price of every billable event to a
// spend total in MongoDB and copies the new totals into Redis. Before ranking,
// the serve path reads what each candidate ad and its campaign have spent, in
// one MGET, and drops the ones that are out of budget or ahead of pace. Ads and
// campaigns with no budget cost no read at all.
//
// Spend is recorded when the render or click arrives, not when the ad is
// served, so an ad can overspend by what is still in flight when it reaches
// its budget. The README works out how much.

// pacingHeadroom lets spend run up to an hour ahead of an even pace, so the day
// can start, and a few cents can never throttle an ad.
const pacingHeadroom = time.Hour

const day = 24 * time.Hour

// Reasons an ad is skipped. They are not logged, because an ad that is out of
// budget would otherwise log on every request.
const (
	reasonTotalBudget = "total budget spent"
	reasonDailyBudget = "daily budget spent"
	reasonPacing      = "ahead of pace"
)

// spendKey names a spend total in Redis. The subscriber writes the same names.
func spendKey(kind, id string) string {
	return "spend:" + kind + ":" + id
}

// dailySpendKey names one UTC day's spend.
func dailySpendKey(kind, id, date string) string {
	return spendKey(kind, id) + ":" + date
}

// limits is a daily and a total budget. Zero means no limit.
type limits struct {
	daily, total cache.Money
}

func (l limits) any() bool {
	return l.daily > 0 || l.total > 0
}

// blockedBy says why something with these limits may not serve now, or "" if it may.
func blockedBy(l limits, spentTotal, spentToday int64, sinceMidnight time.Duration) string {
	if l.total > 0 && spentTotal >= l.total.Nanos() {
		return reasonTotalBudget
	}
	if l.daily > 0 {
		daily := l.daily.Nanos()
		if spentToday >= daily {
			return reasonDailyBudget
		}
		// Pacing is a target, not money, so a float is fine here. The exact
		// limits above are integers.
		fraction := float64(sinceMidnight+pacingHeadroom) / float64(day)
		if fraction < 1 && float64(spentToday) > float64(daily)*fraction {
			return reasonPacing
		}
	}
	return ""
}

// parseSpend reads one spend value from the MGET reply. A missing key has spent
// nothing. A value that is not a number can't show the budget has room, so it
// reports !ok, and only the ad or campaign it belongs to stops serving.
func parseSpend(key, text string) (nanos int64, ok bool) {
	if text == "" {
		return 0, true
	}
	nanos, err := strconv.ParseInt(text, 10, 64)
	if err != nil {
		log.Printf("spend at %s is not a number: %q", key, text)
		return 0, false
	}
	return nanos, true
}

// budgeted is one ad or campaign that has a budget, and where its two spend
// values are in the MGET reply.
type budgeted struct {
	limits       limits
	total, today int
}

// withinBudget returns the ads that may still spend. It reads the spend of every
// budgeted ad and campaign in one round trip, and decides each of them once, so
// a campaign shared by many ads is checked once.
func (server *Server) withinBudget(ads []cache.Ad, campaigns map[string]cache.Campaign) ([]cache.Ad, error) {
	now := server.now().UTC()
	date := now.Format("2006-01-02")
	sinceMidnight := now.Sub(now.Truncate(day))

	type entity struct{ kind, id string }
	position := map[entity]int{} // where each ad or campaign is in budgets
	var budgets []budgeted
	var keys []string
	find := func(kind, id string, l limits) int {
		if !l.any() {
			return -1
		}
		if i, ok := position[entity{kind, id}]; ok {
			return i
		}
		position[entity{kind, id}] = len(budgets)
		budgets = append(budgets, budgeted{limits: l, total: len(keys), today: len(keys) + 1})
		keys = append(keys, spendKey(kind, id), dailySpendKey(kind, id, date))
		return len(budgets) - 1
	}
	adBudget := make([]int, len(ads))
	campaignBudget := make([]int, len(ads))
	for i, ad := range ads {
		adBudget[i] = find("ad", ad.AdID, adLimits(ad))
		campaignBudget[i] = find("campaign", ad.CampaignID, campaignLimits(campaigns[ad.CampaignID]))
	}
	if len(keys) == 0 {
		return ads, nil
	}

	values, err := server.store.MGet(keys)
	if err != nil {
		return nil, err
	}
	if len(values) != len(keys) {
		return nil, fmt.Errorf("asked for %d spend values and got %d", len(keys), len(values))
	}

	blocked := make([]bool, len(budgets))
	for i, b := range budgets {
		total, okTotal := parseSpend(keys[b.total], values[b.total])
		today, okToday := parseSpend(keys[b.today], values[b.today])
		blocked[i] = !okTotal || !okToday || blockedBy(b.limits, total, today, sinceMidnight) != ""
	}

	kept := make([]cache.Ad, 0, len(ads))
	for i, ad := range ads {
		if (adBudget[i] >= 0 && blocked[adBudget[i]]) || (campaignBudget[i] >= 0 && blocked[campaignBudget[i]]) {
			continue
		}
		kept = append(kept, ad)
	}
	return kept, nil
}

func adLimits(ad cache.Ad) limits {
	return limits{daily: ad.Budget.DailyBudget, total: ad.Budget.TotalBudget}
}

func campaignLimits(campaign cache.Campaign) limits {
	return limits{daily: campaign.Budget.DailyBudget, total: campaign.Budget.TotalBudget}
}

// priceNanos is what an ad's billable event costs: a render for CPM, a click for
// CPC. The auction is first price, so the winner pays its bid. A CPM bid is the
// price of a thousand renders, so one render costs the bid's micros in nanos.
func priceNanos(ad cache.Ad) int64 {
	switch ad.BidInfo.BidType {
	case "CPM":
		return ad.BidInfo.Bid.Nanos() / 1000
	case "CPC":
		return ad.BidInfo.Bid.Nanos()
	}
	return 0
}
