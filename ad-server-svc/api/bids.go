package api

import (
	"adserver/cache"
	"adserver/util"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"time"

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
func (server *Server) getBids(bidParams cache.BidParams) (*[]cache.Bid, error) {
	var bids []cache.Bid
	impIDTaken := make(map[string]bool)
	requestTime := time.Now().Unix()
	wanted := distinctImpressionIDs(bidParams.RequestBody.Imp)
	creatives := make(map[string]creativeLookup)

	for _, ad := range *bidParams.RankedAds {
		if len(impIDTaken) >= wanted {
			break
		}

		lookup, seen := creatives[ad.CreativeID]
		if !seen {
			lookup.creative, lookup.err = server.store.GetCreatives(ad.CreativeID)
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
	// URLs to attribute the event.
	iid, err := json.Marshal(cache.IIDData{
		AdID:             ad.AdID,
		CreativeID:       ad.CreativeID,
		AdUnitId:         bidParams.AdUnitId,
		CampaignID:       ad.CampaignID,
		AdvertiserID:     ad.AdvertiserID,
		RequestTimeStamp: requestTime,
	})
	if err != nil {
		return cache.Bid{}, fmt.Errorf("encoding impression id for ad %s: %w", ad.AdID, err)
	}

	adm, err := json.Marshal(asset)
	if err != nil {
		return cache.Bid{}, fmt.Errorf("encoding creative markup for ad %s: %w", ad.AdID, err)
	}

	// With a tracking secret the URLs carry a signature, so the engagement
	// service can tell a URL we issued from one somebody made up.
	encodedIID := base64.StdEncoding.EncodeToString(iid)
	tracking := "?iid=" + encodedIID
	if server.config.TrackingSecret != "" {
		tracking += "&sig=" + util.SignIID(server.config.TrackingSecret, encodedIID)
	}

	return cache.Bid{
		Id:    uuid.New().String(),
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
