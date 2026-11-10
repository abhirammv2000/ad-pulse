package cache

import (
	"encoding/json"
	"log"
)

// CampaignList is the cached list of live campaigns.
//
// Each campaign is decoded on its own. One that can't be read is logged and left
// out, so a single bad row can't stop every other campaign from serving. A value
// that is not a JSON list at all is still an error.
type CampaignList []Campaign

func (list *CampaignList) UnmarshalJSON(data []byte) error {
	var items []json.RawMessage
	if err := json.Unmarshal(data, &items); err != nil {
		return err
	}

	campaigns := make(CampaignList, 0, len(items))
	for i, item := range items {
		var campaign Campaign
		if err := json.Unmarshal(item, &campaign); err != nil {
			log.Printf("skipping campaign %d of the cached list: %v", i, err)
			continue
		}
		campaigns = append(campaigns, campaign)
	}
	*list = campaigns
	return nil
}
