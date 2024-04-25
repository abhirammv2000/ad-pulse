package api

import (
	"adserver/cache"
	"adserver/util"
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func (server *Server) adserve(ctx *gin.Context) {
	var reqParams cache.RequestParams
	if err := ctx.ShouldBindQuery(&reqParams); err != nil {
		ctx.JSON(http.StatusBadRequest, errResponse(err))
		return
	}
	// fmt.Println("reqParams: ", reqParams)
	var reqBody cache.RequestBody
	if err := ctx.ShouldBindJSON(&reqBody); err != nil {
		ctx.JSON(http.StatusBadRequest, errResponse(err))
		return
	}
	adUnitAdress := server.config.AdManagerAddress + "/adunit/" + "ad_unit_id/" + reqParams.AdUnitId
	publisherAdress := server.config.AdManagerAddress + "/publisher/" + "publisherid/" + reqParams.PublisherId

	resp, err := http.Get(publisherAdress)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, errResponse(err))
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		ctx.JSON(http.StatusNotFound, gin.H{"error": "publisher not found"})
		return
	}

	resp, err = http.Get(adUnitAdress)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, errResponse(err))
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		ctx.JSON(http.StatusNotFound, gin.H{"error": "ad unit not found"})
		return
	}

	campaignKey := "campaigns"
	var campaignList []cache.Campaign
	campaigns, err := server.store.Get(campaignKey)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, errResponse(err))
		return
	}
	json.Unmarshal([]byte(campaigns), &campaignList)
	var activeCampaigns []cache.Campaign
	var activeAds []cache.Ad
	var rankedAds []cache.Ad
	var bids *[]cache.Bid
	for _, campaign := range campaignList {
		startDate, err := util.GetTime(campaign.StartDate)
		if err != nil {
			ctx.JSON(http.StatusInternalServerError, errResponse(err))
			return
		}
		endDate, err := util.GetTime(campaign.EndDate)
		if err != nil {
			ctx.JSON(http.StatusInternalServerError, errResponse(err))
			return
		}
		if util.WithinDuration(startDate, endDate) {
			activeCampaigns = append(activeCampaigns, campaign)
			hkey := campaign.CampaignID
			ads, err := server.store.HGetAll(hkey)
			if err != nil {
				ctx.JSON(http.StatusInternalServerError, errResponse(err))
				return
			}
			// fmt.Println("number of ads in campaign: ", len(ads))
			for _, ad := range ads {
				var adObj cache.Ad
				json.Unmarshal([]byte(ad), &adObj)
				// fmt.Println("checking ad: ", adObj.AdID)
				adAvailable, err := util.IsAdAvailable(adObj, reqParams, reqBody)
				if err != nil {
					ctx.JSON(http.StatusInternalServerError, errResponse(err))
					return
				}
				fmt.Println("can ad ", adObj.AdID, " be served: ", adAvailable)
				if adAvailable {
					activeAds = append(activeAds, adObj)
				}
			}

			// fmt.Println("no of active ads: ", len(activeAds))
			rankedAds = util.RankAds(activeAds)
			fmt.Println("ranked ads: ", rankedAds)
			bidParams := cache.BidParams{
				RankedAds:   &rankedAds,
				RequestBody: reqBody,
			}
			bids, err = server.getBids(bidParams)
			if err != nil {
				log.Println(err.Error())
				ctx.JSON(http.StatusInternalServerError, errResponse(err))
				return
			}
		}
	}
	adServeResponse := cache.AdServeResponse{
		Id:    uuid.New().String(),
		Bid:   *bids,
		Bidid: uuid.New().String(),
		Cur:   "USD",
	}
	// fmt.Println("activeAds: ", activeAds)
	// fmt.Println("activeCampaigns: ", activeCampaigns)
	ctx.JSON(http.StatusOK, adServeResponse)
}
