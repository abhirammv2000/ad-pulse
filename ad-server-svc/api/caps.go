package api

import (
	"context"
	"fmt"
	"sort"

	"adserver/cache"
)

// Frequency caps.
//
// A cap limits how many renders or clicks one user may have of an ad, or of any
// ad in a campaign, within a window, such as 3 renders a day. The subscriber keeps
// each user's events in a Redis sorted set per entity and event type, scored by
// the time the ad was served. The serve path counts the members inside each window
// with ZCOUNT, all in one round trip, and drops the ads a user has reached a cap on.
//
// Like spend, events are counted when they arrive, so a user who loads several
// pages within a second can see a capped ad a little more often than the cap.

// maxUserIDLength is the longest user id the caps use. A longer one is treated as no
// user id, so a request can't make the server build huge keys.
const maxUserIDLength = 128

var windowSeconds = map[string]int64{"MINUTE": 60, "HOUR": 3600, "DAY": 86400, "WEEK": 604800}

// counterKey names one user's sorted set of events of one type for one ad or
// campaign. The subscriber writes the same names.
func counterKey(entityType, entityID, eventType, userID string) string {
	return "fc:" + entityType + ":" + entityID + ":" + eventType + ":" + userID
}

// userOf returns the request's user id, or "" if it has none the caps can use.
func userOf(body cache.RequestBody) string {
	if len(body.User.ID) > maxUserIDLength {
		return ""
	}
	return body.User.ID
}

// capsOf returns every cap on an ad: its own and its campaign's.
func capsOf(ad cache.Ad, campaigns map[string]cache.Campaign) []cache.FrequencyCap {
	own := ad.FrequencyCaps.FrequencyCapList
	inherited := campaigns[ad.CampaignID].FrequencyCaps.FrequencyCapList
	if len(inherited) == 0 {
		return own
	}
	return append(append([]cache.FrequencyCap{}, own...), inherited...)
}

// counted says which entity a cap counts events of: the ad itself, or its whole campaign.
func counted(c cache.FrequencyCap, ad cache.Ad) string {
	if c.EntityType == "CAMPAIGN" {
		return ad.CampaignID
	}
	return ad.AdID
}

// countersFor lists the counters an ad's events must feed for its caps, such as
// "AD:CSC", in a fixed order.
func countersFor(caps []cache.FrequencyCap) []string {
	seen := map[string]bool{}
	var names []string
	for _, c := range caps {
		name := c.EntityType + ":" + c.EventType
		if !seen[name] {
			seen[name] = true
			names = append(names, name)
		}
	}
	sort.Strings(names)
	return names
}

// usable reports whether the ad server can apply a cap. ad-manager-svc refuses
// anything else, so this only matters for a row written before it checked.
func usable(c cache.FrequencyCap) bool {
	_, knownWindow := windowSeconds[c.TimeFrame.TimeWindowType]
	return c.UserCap && knownWindow && c.TimeFrame.Value > 0 && c.TimeFrame.MaxCount > 0 &&
		(c.EntityType == "AD" || c.EntityType == "CAMPAIGN") && (c.EventType == "CSC" || c.EventType == "CLK")
}

// withinCaps returns the ads this user has not reached a cap on. An ad with a cap
// can't be checked without a user id, so it is left out, and so is an ad with a
// cap the server can't apply. Ads with no caps cost no read.
func (server *Server) withinCaps(ctx context.Context, ads []cache.Ad, campaigns map[string]cache.Campaign, userID string) ([]cache.Ad, error) {
	now := server.now().Unix()

	type check struct {
		query    int // position in queries
		maxCount int64
	}
	var queries []cache.CountQuery
	position := map[cache.CountQuery]int{}
	checks := make([][]check, len(ads))
	blocked := make([]bool, len(ads))

	for i, ad := range ads {
		for _, c := range capsOf(ad, campaigns) {
			if userID == "" || !usable(c) {
				blocked[i] = true
				break
			}
			since := now - windowSeconds[c.TimeFrame.TimeWindowType]*int64(c.TimeFrame.Value)
			query := cache.CountQuery{Key: counterKey(c.EntityType, counted(c, ad), c.EventType, userID), Since: since}
			p, ok := position[query]
			if !ok {
				p = len(queries)
				position[query] = p
				queries = append(queries, query)
			}
			checks[i] = append(checks[i], check{query: p, maxCount: int64(c.TimeFrame.MaxCount)})
		}
	}

	var counts []int64
	if len(queries) > 0 {
		var err error
		counts, err = server.store.CountSince(ctx, queries)
		if err != nil {
			return nil, err
		}
		if len(counts) != len(queries) {
			return nil, fmt.Errorf("asked for %d event counts and got %d", len(queries), len(counts))
		}
	}

	kept := make([]cache.Ad, 0, len(ads))
	for i, ad := range ads {
		if blocked[i] {
			continue
		}
		capped := false
		for _, c := range checks[i] {
			if counts[c.query] >= c.maxCount {
				capped = true
				break
			}
		}
		if !capped {
			kept = append(kept, ad)
		}
	}
	return kept, nil
}
