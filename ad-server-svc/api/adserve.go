package api

import (
	"adserver/cache"
	"adserver/util"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"net/url"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// adserve answers an ad request for one ad unit.
//
// It walks the cached campaigns, collects the ads that are eligible for this
// request, ranks them, and asks the bidder to match them against the
// impressions the caller offered.
func (server *Server) adserve(ctx *gin.Context) {
	var reqParams cache.RequestParams
	if err := ctx.ShouldBindQuery(&reqParams); err != nil {
		ctx.JSON(http.StatusBadRequest, errResponse(err))
		return
	}

	var reqBody cache.RequestBody
	if err := ctx.ShouldBindJSON(&reqBody); err != nil {
		ctx.JSON(http.StatusBadRequest, errResponse(err))
		return
	}

	if ok := server.entityExists(ctx, "/publisher/publisherid/"+url.PathEscape(reqParams.PublisherId), "publisher"); !ok {
		return
	}
	if ok := server.entityExists(ctx, "/adunit/ad_unit_id/"+url.PathEscape(reqParams.AdUnitId), "ad unit"); !ok {
		return
	}

	campaigns, err := server.store.Get("campaigns")
	if errors.Is(err, cache.ErrNotFound) {
		// The cache has not been filled yet, so there is nothing to serve.
		campaigns = "[]"
	} else if err != nil {
		internalError(ctx, err)
		return
	}

	var campaignList []cache.Campaign
	if err := json.Unmarshal([]byte(campaigns), &campaignList); err != nil {
		internalError(ctx, err)
		return
	}

	// Collect eligible ads across every live campaign first, then rank and bid
	// once. Ranking inside the loop would score each campaign against only a
	// prefix of the candidates.
	var activeAds []cache.Ad
	for _, campaign := range campaignList {
		startDate, err := util.GetTime(campaign.StartDate)
		if err != nil {
			log.Printf("campaign %s has an unparseable start date: %v", campaign.CampaignID, err)
			continue
		}
		endDate, err := util.GetTime(campaign.EndDate)
		if err != nil {
			log.Printf("campaign %s has an unparseable end date: %v", campaign.CampaignID, err)
			continue
		}
		if !util.WithinDuration(startDate, endDate) {
			continue
		}

		ads, err := server.store.HGetAll(campaign.CampaignID)
		if err != nil {
			internalError(ctx, err)
			return
		}

		for _, ad := range ads {
			var adObj cache.Ad
			if err := json.Unmarshal([]byte(ad), &adObj); err != nil {
				log.Printf("skipping malformed ad in campaign %s: %v", campaign.CampaignID, err)
				continue
			}
			if util.IsAdAvailable(adObj, reqParams) {
				activeAds = append(activeAds, adObj)
			}
		}
	}

	if len(activeAds) == 0 {
		ctx.JSON(http.StatusNoContent, nil)
		return
	}

	rankedAds := util.RankAds(activeAds)
	bids, err := server.getBids(cache.BidParams{
		RankedAds:   &rankedAds,
		RequestBody: reqBody,
		AdUnitId:    reqParams.AdUnitId,
	})
	if err != nil {
		log.Printf("no bid for ad unit %s: %v", reqParams.AdUnitId, err)
		ctx.JSON(http.StatusNoContent, nil)
		return
	}

	ctx.JSON(http.StatusOK, cache.AdServeResponse{
		Id:    uuid.New().String(),
		Bid:   *bids,
		Bidid: uuid.New().String(),
		Cur:   "USD",
	})
}

// entityExists checks the ad manager for a publisher or ad unit, writing the
// error response itself and reporting whether the caller should continue.
func (server *Server) entityExists(ctx *gin.Context, path, label string) bool {
	req, err := http.NewRequestWithContext(ctx.Request.Context(), http.MethodGet, server.config.AdManagerAddress+path, nil)
	if err != nil {
		internalError(ctx, err)
		return false
	}
	resp, err := server.httpClient.Do(req)
	if err != nil {
		log.Printf("cannot check the %s with the ad manager: %v", label, err)
		ctx.JSON(http.StatusBadGateway, gin.H{"error": "could not check the " + label})
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		ctx.JSON(http.StatusNotFound, gin.H{"error": label + " not found"})
		return false
	}
	return true
}
