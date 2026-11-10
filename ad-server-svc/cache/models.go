package cache

type RequestParams struct {
	AdUnitId    string `form:"adunit_id" binding:"required"`
	PublisherId string `form:"publisher_id" binding:"required"`
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
	DPL  string       `json:"dpl"`
	ID   string       `json:"id"`
	Imp  []Impression `json:"imp"`
	User struct {
		ID string `json:"id"` // who the ad is for, as OpenRTB's user.id. Frequency caps count per user
	} `json:"user"`
}

type Campaign struct {
	CampaignID   string `json:"campaignid"`
	CampaignName string `json:"campaignname"`
	StartDate    string `json:"startdate"`
	Budget       struct {
		DailyBudget  Money  `json:"dailyBudget"`
		TotalBudget  Money  `json:"totalBudget"`
		CurrencyCode string `json:"currencyCode"`
	} `json:"budget"`
	CreatedAt     string        `json:"createdat"`
	UpdatedAt     string        `json:"updatedat"`
	UpdatedBy     string        `json:"updatedby"`
	AdvertiserID  string        `json:"advertiserid"`
	EndDate       string        `json:"enddate"`
	FrequencyCaps FrequencyCaps `json:"frequencycaps"`
	CreatedBy     string        `json:"createdby"`
	CampaignState string        `json:"campaignstate"`
}

// FrequencyCap limits how many renders (CSC) or clicks (CLK) one user may have of
// an ad, or of any ad in a campaign (EntityType), within a window. ad-manager-svc
// checks the values before they are stored.
type FrequencyCap struct {
	UserCap   bool   `json:"userCap"`
	EventType string `json:"eventType"`
	TimeFrame struct {
		Value          int    `json:"value"`
		MaxCount       int    `json:"maxCount"`
		TimeWindowType string `json:"timeWindowType"`
	} `json:"timeFrame"`
	EntityType string `json:"entityType"`
}

type FrequencyCaps struct {
	FrequencyCapList []FrequencyCap `json:"frequencyCapList"`
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
		Bid     Money  `json:"bid"`
		BidType string `json:"bidType"`
	} `json:"bidinfo"`
	Budget struct {
		CurrencyCode string `json:"currencyCode"`
		DailyBudget  Money  `json:"dailyBudget"`
		TotalBudget  Money  `json:"totalBudget"`
	} `json:"budget"`
	CampaignID    string         `json:"campaignid"`
	CreatedAt     string         `json:"createdat"`
	CreatedBy     string         `json:"createdby"`
	CreativeID    string         `json:"creativeid"`
	EndDate       string         `json:"enddate"`
	FrequencyCaps FrequencyCaps  `json:"frequencycaps"`
	LandingURL    string         `json:"landingurl"`
	StartDate     string         `json:"startdate"`
	TargetingInfo *TargetingInfo `json:"targetinginfo"`
	UpdatedAt     string         `json:"updatedat"`
	UpdatedBy     string         `json:"updatedby"`

	// The ad's clicks and renders so far. ad-manager-svc's cache job adds them to CPC
	// ads, whose ranking needs a click-through rate. Other ads have none.
	Stats struct {
		Clicks  int64 `json:"clicks"`
		Renders int64 `json:"renders"`
	} `json:"stats"`

	flight *flight // StartDate and EndDate, parsed once when decoded. See flight.go
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

type CreativeAsset struct {
	Type      string `json:"type"`
	Required  bool   `json:"required"`
	Height    int    `json:"height"`
	Width     int    `json:"width"`
	ImageURL  string `json:"imageURL"`
	ImageType string `json:"imageType"`
}

type Creative struct {
	Type         string          `json:"type"`
	Name         string          `json:"name"`
	State        string          `json:"state"`
	AdvertiserID string          `json:"advertiserId"`
	CreatedBy    string          `json:"createdBy"`
	UpdatedBy    string          `json:"updatedBy"`
	CreatedAt    string          `json:"createdAt"`
	UpdatedAt    string          `json:"updatedAt"`
	Assets       []CreativeAsset `json:"assets"`
}

// IIDData identifies one served bid. It travels in the click and render URLs,
// signed, and the bid id is what lets each event be counted only once.
//
// BidType and PriceNanos say what the bid costs: a render for CPM, a click for
// CPC. They are fixed when the ad is served, so changing an ad's bid later never
// changes what its earlier events cost.
type IIDData struct {
	BidID            string `json:"bidid"`
	BidType          string `json:"bidtype"`
	PriceNanos       int64  `json:"pricenanos"`
	AdID             string `json:"adid"`
	CreativeID       string `json:"creativeid"`
	AdUnitId         string `json:"adunitid"`
	CampaignID       string `json:"campaignid"`
	AdvertiserID     string `json:"advertiserid"`
	RequestTimeStamp int64  `json:"requesttimestamp"`

	// For frequency caps: the user, and which of their counters this event feeds,
	// such as "AD:CSC" for renders of this ad. Only set when the ad or its campaign
	// has a cap and the request named a user.
	UserID   string   `json:"userid,omitempty"`
	Counters []string `json:"counters,omitempty"`
}

type AdServeResponse struct {
	Id    string `json:"id"`
	Bid   []Bid  `json:"bid"`
	Bidid string `json:"bidid"`
	Cur   string `json:"cur"`
}

type BidParams struct {
	RequestBody RequestBody         `json:"request_body"`
	AdUnitId    string              `json:"adunit_id"`
	UserID      string              `json:"user_id"`
	Counters    map[string][]string `json:"counters"` // by ad id, see IIDData.Counters
}
