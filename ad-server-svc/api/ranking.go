package api

import (
	"container/heap"
	"strings"

	"adserver/cache"
)

// Ranking.
//
// Ads are ordered by priority first, lowest number first, the way Google Ad Manager
// puts guaranteed deals ahead of open competition. Within a priority they compete on
// eCPM, what a thousand impressions are expected to pay, which puts CPM and CPC ads
// on one scale. Ties go to the lower ad id, so the order never changes between
// requests.
//
// Nothing is sorted up front. A request usually fills one or two slots from hundreds
// of candidates, so the candidates go into a heap, which takes O(n) to build, and the
// bidder takes the best one left, in O(log n), only as long as it still has slots to
// fill. Sorting every ad, and moving the ads themselves rather than small keys, was
// the largest CPU cost of a request.

// A CPC ad's eCPM needs its click-through rate. A new ad has no history, and one click
// in two renders is not a 50% rate, so its own clicks and renders are blended with a
// prior: one click per hundred renders, worth a hundred renders of evidence.
const (
	priorCTR    = 0.01
	priorWeight = 100.0
)

// expectedCTR is the mean of a Beta prior updated with the ad's own clicks and
// renders. It starts at the prior and moves to the ad's own rate as renders add up.
func expectedCTR(clicks, renders int64) float64 {
	return (float64(clicks) + priorCTR*priorWeight) / (float64(renders) + priorWeight)
}

// ecpm is what a thousand impressions of the ad are expected to pay, in nanos. It
// only orders ads, so a float is fine. Billing uses the exact price, see priceNanos.
func ecpm(ad cache.Ad) float64 {
	bid := float64(ad.BidInfo.Bid.Nanos())
	switch ad.BidInfo.BidType {
	case "CPM":
		return bid
	case "CPC":
		return bid * expectedCTR(ad.Stats.Clicks, ad.Stats.Renders) * 1000
	}
	return 0
}

type rankKey struct {
	priority int
	ecpm     float64
	id       string
	index    int // position in ranking.ads
}

// better reports whether a should win a slot before b.
func better(a, b rankKey) bool {
	if a.priority != b.priority {
		return a.priority < b.priority
	}
	if a.ecpm != b.ecpm {
		return a.ecpm > b.ecpm
	}
	if c := strings.Compare(a.id, b.id); c != 0 {
		return c < 0
	}
	return a.index < b.index
}

// rankHeap keeps the best key at the top, for container/heap.
type rankHeap []rankKey

func (h rankHeap) Len() int           { return len(h) }
func (h rankHeap) Less(i, j int) bool { return better(h[i], h[j]) }
func (h rankHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *rankHeap) Push(x any)        { *h = append(*h, x.(rankKey)) }
func (h *rankHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

// ranking hands out the candidates best first, one at a time.
type ranking struct {
	ads  []cache.Ad
	keys rankHeap
}

func newRanking(ads []cache.Ad) *ranking {
	keys := make(rankHeap, len(ads))
	for i, ad := range ads {
		keys[i] = rankKey{priority: ad.AdPriority, ecpm: ecpm(ad), id: ad.AdID, index: i}
	}
	heap.Init(&keys)
	return &ranking{ads: ads, keys: keys}
}

// next returns the best ad not handed out yet, or false when none are left.
func (r *ranking) next() (cache.Ad, bool) {
	if len(r.keys) == 0 {
		return cache.Ad{}, false
	}
	key := heap.Pop(&r.keys).(rankKey)
	return r.ads[key.index], true
}
