package api

import (
	"adserver/cache"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
)

func (server *Server) getBids(bidParams cache.BidParams) (*[]cache.Bid, error) {
	var bids []cache.Bid
	var impIDTaken = make(map[string]bool)
	currentTime := time.Now().Unix()
	ads := bidParams.RankedAds
	adBody := bidParams.RequestBody
	for _, ad := range *ads {
		bidAssigned := false
		creative, err := server.store.GetCreatives(ad.CreativeID)
		if err != nil {
			fmt.Println("Error getting creatives:", err)
			return nil, err
		}
		for _, asset := range creative.Assets {
			if asset.Type == "IMAGE" {
				for _, imp := range adBody.Imp {
					if _, ok := impIDTaken[imp.ID]; ok {
						// fmt.Println("impID already taken: ", imp.ID)
						continue
					}
					for _, img := range imp.Native.Request.Assets {
						// fmt.Println("checking image: ", img.Img.Type, img.Img.W == asset.Width, img.Img.H == asset.Height, imp.ID)
						if img.Img.Type == 3 && img.Img.W == asset.Width && img.Img.H == asset.Height {
							iidData := cache.IIDData{
								AdID:             ad.AdID,
								CreativeID:       ad.CreativeID,
								AdUnitId:         adBody.ID,
								CampaignID:       ad.CampaignID,
								RequestTimeStamp: currentTime,
								AdvertiserID:     ad.AdvertiserID,
							}
							jsonData, err := json.Marshal(iidData)
							if err != nil {
								fmt.Println("Error marshalling JSON:", err)
								return nil, err
							}
							admJSON, err := json.Marshal(asset)
							if err != nil {
								fmt.Println("Error marshalling to JSON:", err)
								return nil, err
							}
							formClickUrl := server.config.ClickUrl + "?iid=" + base64.StdEncoding.EncodeToString([]byte(jsonData))
							formRenderUrl := server.config.RenderUrl + "?iid=" + base64.StdEncoding.EncodeToString([]byte(jsonData))
							newBid := cache.Bid{
								Id:    uuid.New().String(),
								Impid: imp.ID,
								AdID:  ad.AdID,
								Adm:   string(admJSON),
								Cid:   ad.CampaignID,
								Crid:  ad.CreativeID,
								Ext: cache.Ext{
									ClickUrl:   formClickUrl,
									AdType:     "NATIVE",
									Kslotid:    adBody.ID + "_" + imp.ID,
									AdEndTime:  ad.EndDate,
									LandingUrl: ad.LandingURL,
									RenderUrl:  formRenderUrl,
								},
							}
							bids = append(bids, newBid)
							impIDTaken[imp.ID] = true
							bidAssigned = true
							break
						}
					}
					if bidAssigned {
						break
					}
				}
			}
			if bidAssigned {
				break
			}
		}
	}
	if len(bids) == 0 {
		return nil, fmt.Errorf("no ads available")
	}
	return &bids, nil
}
