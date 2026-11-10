package api

import (
	"adserver/cache"
	"adserver/util"
	"context"
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

	// Every Redis call of this request shares one deadline, so a slow Redis can't
	// hold a request for long. Past it the request fails and nothing is served.
	rctx := ctx.Request.Context()
	if server.config.RedisTimeout > 0 {
		var cancel context.CancelFunc
		rctx, cancel = context.WithTimeout(rctx, server.config.RedisTimeout)
		defer cancel()
	}

	campaigns, err := server.store.Get(rctx, "campaigns")
	if errors.Is(err, cache.ErrNotFound) {
		// The cache has not been filled yet, so there is nothing to serve.
		campaigns = "[]"
	} else if err != nil {
		internalError(ctx, err)
		return
	}

	campaignList, err := server.campaignsDecoded.get(campaigns)
	if err != nil {
		internalError(ctx, err)
		return
	}

	// Collect eligible ads across every live campaign first, then rank and bid
	// once. Ranking inside the loop would score each campaign against only a
	// prefix of the candidates.
	var activeAds []cache.Ad
	liveCampaigns := map[string]cache.Campaign{}
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
		liveCampaigns[campaign.CampaignID] = campaign

		ads, err := server.store.HGetAll(rctx, campaign.CampaignID)
		if err != nil {
			internalError(ctx, err)
			return
		}

		for _, ad := range ads {
			adObj, err := server.adsDecoded.get(ad)
			if err != nil {
				log.Printf("skipping malformed ad in campaign %s: %v", campaign.CampaignID, err)
				continue
			}
			if util.IsAdAvailable(adObj, reqParams) {
				activeAds = append(activeAds, adObj)
			}
		}
	}

	activeAds, err = server.withinBudget(rctx, activeAds, liveCampaigns)
	if err != nil {
		internalError(ctx, err)
		return
	}

	userID := userOf(reqBody)
	activeAds, err = server.withinCaps(rctx, activeAds, liveCampaigns, userID)
	if err != nil {
		internalError(ctx, err)
		return
	}

	// The events of a capped ad must feed this user's counters, so its tracking
	// URLs say which ones.
	counters := map[string][]string{}
	if userID != "" {
		for _, ad := range activeAds {
			if caps := capsOf(ad, liveCampaigns); len(caps) > 0 {
				counters[ad.AdID] = countersFor(caps)
			}
		}
	}

	if len(activeAds) == 0 {
		ctx.JSON(http.StatusNoContent, nil)
		return
	}

	bids, err := server.getBids(rctx, newRanking(activeAds), cache.BidParams{
		RequestBody: reqBody,
		AdUnitId:    reqParams.AdUnitId,
		UserID:      userID,
		Counters:    counters,
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
// A 200 is remembered for a short time, see knownEntities.
func (server *Server) entityExists(ctx *gin.Context, path, label string) bool {
	if server.known.has(path) {
		return true
	}

	req, err := http.NewRequestWithContext(ctx.Request.Context(), http.MethodGet, server.config.AdManagerAddress+path, nil)
	if err != nil {
		internalError(ctx, err)
		return false
	}
	if server.config.AdManagerAPIKey != "" {
		req.Header.Set(adManagerAPIKeyHeader, server.config.AdManagerAPIKey)
	}
	resp, err := server.httpClient.Do(req)
	if err != nil {
		log.Printf("cannot check the %s with the ad manager: %v", label, err)
		ctx.JSON(http.StatusBadGateway, gin.H{"error": "could not check the " + label})
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		// A rejected key is a configuration fault, not a missing publisher. Saying "not found" here would make
		// every ad request fail with a misleading error.
		log.Printf("the ad manager rejected the API key while checking the %s; check AD_MANAGER_API_KEY", label)
		ctx.JSON(http.StatusBadGateway, gin.H{"error": "could not check the " + label})
		return false
	}
	if resp.StatusCode != http.StatusOK {
		ctx.JSON(http.StatusNotFound, gin.H{"error": label + " not found"})
		return false
	}
	server.known.remember(path)
	return true
}
