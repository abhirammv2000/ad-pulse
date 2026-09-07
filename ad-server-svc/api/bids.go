package api

import (
	"adserver/cache"
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
func (server *Server) getBids(bidParams cache.BidParams) (*[]cache.Bid, error) {
	var bids []cache.Bid
	impIDTaken := make(map[string]bool)
	requestTime := time.Now().Unix()

	for _, ad := range *bidParams.RankedAds {
		creative, err := server.store.GetCreatives(ad.CreativeID)
		if err != nil {
			// One unreadable creative should not sink the whole request.
			log.Printf("skipping ad %s: cannot load creative %s: %v", ad.AdID, ad.CreativeID, err)
			continue
		}

		asset, impID, ok := matchImpression(creative, bidParams.RequestBody.Imp, impIDTaken)
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

	encodedIID := base64.StdEncoding.EncodeToString(iid)
	return cache.Bid{
		Id:    uuid.New().String(),
		Impid: impID,
		AdID:  ad.AdID,
		Adm:   string(adm),
		Cid:   ad.CampaignID,
		Crid:  ad.CreativeID,
		Ext: cache.Ext{
			ClickUrl:   server.config.ClickUrl + "?iid=" + encodedIID,
			AdType:     "NATIVE",
			Kslotid:    bidParams.RequestBody.ID + "_" + impID,
			AdEndTime:  ad.EndDate,
			LandingUrl: ad.LandingURL,
			RenderUrl:  server.config.RenderUrl + "?iid=" + encodedIID,
		},
	}, nil
}
