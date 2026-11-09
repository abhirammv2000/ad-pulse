package cache

import (
	"encoding/json"
	"testing"
)

func TestCampaignList_SkipsCampaignsThatCannotBeRead(t *testing.T) {
	raw := `[{"campaignid":"C1"},{"campaignid":"BAD","budget":{"dailyBudget":"10"}},"oops",null,{"campaignid":"C2"}]`

	var list CampaignList
	if err := json.Unmarshal([]byte(raw), &list); err != nil {
		t.Fatal(err)
	}

	// null decodes to an empty campaign, which the serve path skips for its missing dates.
	var ids []string
	for _, campaign := range list {
		ids = append(ids, campaign.CampaignID)
	}
	if len(ids) != 3 || ids[0] != "C1" || ids[1] != "" || ids[2] != "C2" {
		t.Errorf("got %q, want C1, an empty campaign and C2", ids)
	}
}

func TestCampaignList_AValueThatIsNotAListIsAnError(t *testing.T) {
	for _, raw := range []string{`{not json`, `{"campaignid":"C1"}`, `"campaigns"`} {
		var list CampaignList
		if err := json.Unmarshal([]byte(raw), &list); err == nil {
			t.Errorf("%s: want an error", raw)
		}
	}
}

func TestCampaignList_NullIsEmpty(t *testing.T) {
	var list CampaignList
	if err := json.Unmarshal([]byte(`null`), &list); err != nil || len(list) != 0 {
		t.Errorf("got %v, %v, want an empty list", list, err)
	}
}
