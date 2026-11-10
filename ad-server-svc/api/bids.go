package api

import (
	"adserver/cache"
	"adserver/util"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/url"

	"github.com/google/uuid"
)

// imageAssetType is the OpenRTB native asset type for a main image.
const imageAssetType = 3

// getBids matches each ranked ad against the impressions on offer, at most one
// bid per impression and at most one bid per ad.
//
// Each creative is read from the cache once per request, and the walk stops as
// soon as every impression has a bid: a later ad could not match anything, so
// reading its creative would only cost a round trip.
func (server *Server) getBids(ctx context.Context, candidates *ranking, bidParams cache.BidParams) (*[]cache.Bid, error) {
	var bids []cache.Bid
	impIDTaken := make(map[string]bool)
	// The same clock as the cap windows: a cap counts events by this time.
	requestTime := server.now().Unix()
	wanted := distinctImpressionIDs(bidParams.RequestBody.Imp)
	creatives := make(map[string]creativeLookup)

	for len(impIDTaken) < wanted {
		ad, ok := candidates.next()
		if !ok {
			break
		}

		lookup, seen := creatives[ad.CreativeID]
		if !seen {
			lookup.creative, lookup.err = server.store.GetCreatives(ctx, ad.CreativeID)
			creatives[ad.CreativeID] = lookup
		}
		if lookup.err != nil {
			// One unreadable creative should not sink the whole request.
			log.Printf("skipping ad %s: cannot load creative %s: %v", ad.AdID, ad.CreativeID, lookup.err)
			continue
		}

		asset, impID, ok := matchImpression(lookup.creative, bidParams.RequestBody.Imp, impIDTaken)
		if !ok {
			continue
		}

		bid, err := server.buildBid(ad, asset, impID, bidParams, requestTime)
		if err != nil {
			return nil, err
		}

		bids = append(bids, bid)
		impIDTaken[impID] = true
	}

	if len(bids) == 0 {
		return nil, fmt.Errorf("no ads available")
	}
	return &bids, nil
}

// creativeLookup is what the cache answered for one creative id, kept for the rest of the request.
type creativeLookup struct {
	creative *cache.Creative
	err      error
}

// distinctImpressionIDs counts the impressions a bid can still be made for. Impressions that share an id share one
// slot, because the taken map is keyed by id.
func distinctImpressionIDs(impressions []cache.Impression) int {
	ids := make(map[string]struct{}, len(impressions))
	for _, imp := range impressions {
		ids[imp.ID] = struct{}{}
	}
	return len(ids)
}

// matchImpression finds the first free impression whose requested image
// dimensions match one of the creative's image assets.
func matchImpression(creative *cache.Creative, impressions []cache.Impression, taken map[string]bool) (cache.CreativeAsset, string, bool) {
	for _, asset := range creative.Assets {
		if asset.Type != "IMAGE" {
			continue
		}
		for _, imp := range impressions {
			if taken[imp.ID] {
				continue
			}
			for _, requested := range imp.Native.Request.Assets {
				if requested.Img.Type == imageAssetType &&
					requested.Img.W == asset.Width &&
					requested.Img.H == asset.Height {
					return asset, imp.ID, true
				}
			}
		}
	}
	return cache.CreativeAsset{}, "", false
}

func (server *Server) buildBid(ad cache.Ad, asset cache.CreativeAsset, impID string, bidParams cache.BidParams, requestTime int64) (cache.Bid, error) {
	// The engagement service decodes this blob back out of the click and render
	// URLs to attribute the event. Both URLs carry the same bid id, so one served
	// bid can be counted for at most one click and one render.
	bidID := uuid.New().String()
	identity := cache.IIDData{
		BidID:            bidID,
		BidType:          ad.BidInfo.BidType,
		PriceNanos:       priceNanos(ad),
		AdID:             ad.AdID,
		CreativeID:       ad.CreativeID,
		AdUnitId:         bidParams.AdUnitId,
		CampaignID:       ad.CampaignID,
		AdvertiserID:     ad.AdvertiserID,
		RequestTimeStamp: requestTime,
	}
	// Only a capped ad's URLs carry the user id, because only they need it.
	if counters := bidParams.Counters[ad.AdID]; len(counters) > 0 {
		identity.UserID, identity.Counters = bidParams.UserID, counters
	}
	iid, err := json.Marshal(identity)
	if err != nil {
		return cache.Bid{}, fmt.Errorf("encoding impression id for ad %s: %w", ad.AdID, err)
	}

	adm, err := json.Marshal(asset)
	if err != nil {
		return cache.Bid{}, fmt.Errorf("encoding creative markup for ad %s: %w", ad.AdID, err)
	}

	// With a tracking secret the URLs carry a signature, so the engagement
	// service can tell a URL we issued from one somebody made up. The signature
	// is over the base64 text, which is escaped for the URL: base64 can contain
	// "+", and a query string would read that as a space.
	encodedIID := base64.StdEncoding.EncodeToString(iid)
	tracking := "?iid=" + url.QueryEscape(encodedIID)
	if server.config.TrackingSecret != "" {
		tracking += "&sig=" + util.SignIID(server.config.TrackingSecret, encodedIID)
	}

	return cache.Bid{
		Id:    bidID,
		Impid: impID,
		AdID:  ad.AdID,
		Adm:   string(adm),
		Cid:   ad.CampaignID,
		Crid:  ad.CreativeID,
		Ext: cache.Ext{
			ClickUrl:   server.config.ClickUrl + tracking,
			AdType:     "NATIVE",
			Kslotid:    bidParams.RequestBody.ID + "_" + impID,
			AdEndTime:  ad.EndDate,
			LandingUrl: ad.LandingURL,
			RenderUrl:  server.config.RenderUrl + tracking,
		},
	}, nil
}
