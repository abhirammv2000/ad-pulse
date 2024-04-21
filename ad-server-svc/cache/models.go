package cache

type RequestParams struct {
	AdUnitId    string `form:"adunit_id"`
	PublisherId string `form:"publisher_id"`
}

type Img struct {
	Type int `json:"type"`
	W    int `json:"w"`
	H    int `json:"h"`
}

type Asset struct {
	ID       int `json:"id"`
	Required int `json:"required"`
	Img      Img `json:"img"`
}

type Native struct {
	Request struct {
		Ver    string  `json:"ver"`
		Assets []Asset `json:"assets"`
	} `json:"request"`
	Ver string `json:"ver"`
}

type Impression struct {
	BidFloorCur string `json:"bidfloorcur"`
	ID          string `json:"id"`
	Native      Native `json:"native"`
}

type RequestBody struct {
	DPL string       `json:"dpl"`
	ID  string       `json:"id"`
	Imp []Impression `json:"imp"`
}

type Campaign struct {
	CampaignID   string `json:"campaignid"`
	CampaignName string `json:"campaignname"`
	StartDate    string `json:"startdate"`
	Budget       struct {
		DailyBudget  int    `json:"dailyBudget"`
		TotalBudget  int    `json:"totalBudget"`
		CurrencyCode string `json:"currencyCode"`
	} `json:"budget"`
	CreatedAt     string `json:"createdat"`
	UpdatedAt     string `json:"updatedat"`
	UpdatedBy     string `json:"updatedby"`
	AdvertiserID  string `json:"advertiserid"`
	EndDate       string `json:"enddate"`
	FrequencyCaps struct {
		FrequencyCapList []struct {
			UserCap   bool   `json:"userCap"`
			EventType string `json:"eventType"`
			TimeFrame struct {
				Value          int    `json:"value"`
				MaxCount       int    `json:"maxCount"`
				TimeWindowType string `json:"timeWindowType"`
			} `json:"timeFrame"`
			EntityType string `json:"entityType"`
		} `json:"frequencyCapList"`
	} `json:"frequencycaps"`
	CreatedBy     string `json:"createdby"`
	CampaignState string `json:"campaignstate"`
}

type DayTargeting struct {
	Type   string `json:"type"`
	Values []int  `json:"values"`
}

type TimeTargeting struct {
	Type   string `json:"type"`
	Values []int  `json:"values"`
}

type TargetingInfo struct {
	DayTargeting  DayTargeting  `json:"dayTargeting"`
	TimeTargeting TimeTargeting `json:"timeTargeting"`
}

type Ad struct {
	AdID           string   `json:"adid"`
	AdUnitTargeted []string `json:"ad_unit_targeted"`
	AdName         string   `json:"adname"`
	AdPriority     int      `json:"adpriority"`
	AdState        string   `json:"adstate"`
	AdType         string   `json:"adtype"`
	AdvertiserID   string   `json:"advertiserid"`
	BidInfo        struct {
		Bid     int    `json:"bid"`
		BidType string `json:"bidType"`
	} `json:"bidinfo"`
	Budget struct {
		CurrencyCode string `json:"currencyCode"`
		DailyBudget  int    `json:"dailyBudget"`
		TotalBudget  int    `json:"totalBudget"`
	} `json:"budget"`
	CampaignID    string `json:"campaignid"`
	CreatedAt     string `json:"createdat"`
	CreatedBy     string `json:"createdby"`
	CreativeID    string `json:"creativeid"`
	EndDate       string `json:"enddate"`
	FrequencyCaps struct {
		FrequencyCapList []struct {
			UserCap   bool   `json:"userCap"`
			EventType string `json:"eventType"`
			TimeFrame struct {
				Value          int    `json:"value"`
				MaxCount       int    `json:"maxCount"`
				TimeWindowType string `json:"timeWindowType"`
			} `json:"timeFrame"`
			EntityType string `json:"entityType"`
		} `json:"frequencyCapList"`
	} `json:"frequencycaps"`
	LandingURL    string         `json:"landingurl"`
	StartDate     string         `json:"startdate"`
	TargetingInfo *TargetingInfo `json:"targetinginfo"`
	UpdatedAt     string         `json:"updatedat"`
	UpdatedBy     string         `json:"updatedby"`
}

type Ext struct {
	ClickUrl   string `json:"clickUrl"`
	AdType     string `json:"adType"`
	Kslotid    string `json:"kslotid"`
	AdEndTime  string `json:"adEndTime"`
	LandingUrl string `json:"landingUrl"`
	RenderUrl  string `json:"renderUrl"`
}

type Bid struct {
	Id    string `json:"id"`
	Impid string `json:"impid"`
	AdID  string `json:"adid"`
	Adm   string `json:"adm"`
	Cid   string `json:"cid"`
	Crid  string `json:"crid"`
	Ext   Ext    `json:"ext"`
}

type Creative struct {
	Type         string `json:"type"`
	Name         string `json:"name"`
	State        string `json:"state"`
	AdvertiserID string `json:"advertiserId"`
	CreatedBy    string `json:"createdBy"`
	UpdatedBy    string `json:"updatedBy"`
	CreatedAt    string `json:"createdAt"`
	UpdatedAt    string `json:"updatedAt"`
	Assets       []struct {
		Type      string `json:"type"`
		Required  bool   `json:"required"`
		Height    int    `json:"height"`
		Width     int    `json:"width"`
		ImageURL  string `json:"imageURL"`
		ImageType string `json:"imageType"`
	} `json:"assets"`
}

type IIDData struct {
	AdID             string `json:"adid"`
	CreativeID       string `json:"creativeid"`
	AdUnitId         string `json:"adunitid"`
	CampaignID       string `json:"campaignid"`
	AdvertiserID     string `json:"advertiserid"`
	RequestTimeStamp int64  `json:"requesttimestamp"`
}

type AdServeResponse struct {
	Id    string `json:"id"`
	Bid   []Bid  `json:"bid"`
	Bidid string `json:"bidid"`
	Cur   string `json:"cur"`
}

type BidParams struct {
	RankedAds   *[]Ad       `json:"ranked_ads"`
	RequestBody RequestBody `json:"request_body"`
}
