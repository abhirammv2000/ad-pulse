package api

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	neturl "net/url"
	"strings"
	"testing"
	"time"

	"adserver/cache"
	"adserver/util"

	"github.com/gin-gonic/gin"
)

func init() {
	gin.SetMode(gin.TestMode)
}

const dateLayout = "2006-01-02T15:04:05"

// fakeStore is an in-memory cache.Store.
type fakeStore struct {
	values map[string]string
	hashes map[string]map[string]string
	getErr error
}

func newFakeStore() *fakeStore {
	return &fakeStore{values: map[string]string{}, hashes: map[string]map[string]string{}}
}

func (f *fakeStore) Get(key string) (string, error) {
	if f.getErr != nil {
		return "", f.getErr
	}
	value, ok := f.values[key]
	if !ok {
		return "", cache.ErrNotFound
	}
	return value, nil
}

func (f *fakeStore) Set(key, value string) error {
	f.values[key] = value
	return nil
}

func (f *fakeStore) HGetAll(key string) (map[string]string, error) {
	return f.hashes[key], nil
}

func (f *fakeStore) GetCreatives(creativeID string) (*cache.Creative, error) {
	raw, err := f.Get(creativeID)
	if err != nil {
		return nil, err
	}
	var creative cache.Creative
	if err := json.Unmarshal([]byte(raw), &creative); err != nil {
		return nil, err
	}
	return &creative, nil
}

func mustJSON(t *testing.T, value any) string {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

// adManager stands in for ad-manager-svc: P1 and ADU1 exist, nothing else does.
func adManager(t *testing.T) *httptest.Server {
	t.Helper()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/publisher/publisherid/P1", "/adunit/ad_unit_id/ADU1":
			w.WriteHeader(http.StatusOK)
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	t.Cleanup(server.Close)
	return server
}

func newTestServer(t *testing.T, store cache.Store, managerURL string) *Server {
	t.Helper()
	server, err := NewServer(util.Config{
		AdManagerAddress: managerURL,
		ClickUrl:         "http://engagement/clk",
		RenderUrl:        "http://engagement/csc",
	}, store)
	if err != nil {
		t.Fatal(err)
	}
	return server
}

func window(start, end time.Duration) (string, string) {
	now := time.Now().UTC()
	return now.Add(start).Format(dateLayout), now.Add(end).Format(dateLayout)
}

// seedCampaign caches one live campaign with the given ads, plus one 300x250
// image creative called CR1.
func seedCampaign(t *testing.T, store *fakeStore, ads ...cache.Ad) {
	t.Helper()
	start, end := window(-time.Hour, time.Hour)
	store.values["campaigns"] = mustJSON(t, []cache.Campaign{
		{CampaignID: "C1", StartDate: start, EndDate: end},
	})
	store.hashes["C1"] = map[string]string{}
	for _, ad := range ads {
		store.hashes["C1"][ad.AdID] = mustJSON(t, ad)
	}
	store.values["CR1"] = mustJSON(t, cache.Creative{
		Assets: []cache.CreativeAsset{{Type: "IMAGE", Width: 300, Height: 250, ImageURL: "http://img/1.png"}},
	})
}

func liveAd(id string, priority int) cache.Ad {
	start, end := window(-time.Hour, time.Hour)
	return cache.Ad{
		AdID: id, CampaignID: "C1", AdvertiserID: "A1", CreativeID: "CR1",
		StartDate: start, EndDate: end, AdPriority: priority, LandingURL: "http://landing",
	}
}

func impression(id string, width, height int) cache.Impression {
	imp := cache.Impression{ID: id}
	imp.Native.Request.Assets = []cache.Asset{{ID: 1, Img: cache.Img{Type: 3, W: width, H: height}}}
	return imp
}

func serve(t *testing.T, server *Server, query string, body cache.RequestBody) *httptest.ResponseRecorder {
	t.Helper()
	request := httptest.NewRequest(http.MethodPost, "/adserve?"+query, bytes.NewBufferString(mustJSON(t, body)))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()
	server.router.ServeHTTP(recorder, request)
	return recorder
}

const validQuery = "adunit_id=ADU1&publisher_id=P1"

func slotRequest() cache.RequestBody {
	return cache.RequestBody{ID: "req1", Imp: []cache.Impression{impression("imp1", 300, 250)}}
}

func decodeResponse(t *testing.T, recorder *httptest.ResponseRecorder) cache.AdServeResponse {
	t.Helper()
	var response cache.AdServeResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatalf("response is not an ad response: %v\n%s", err, recorder.Body.String())
	}
	return response
}

func TestAdserve_ReturnsABidForAMatchingAd(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server := newTestServer(t, store, adManager(t).URL)

	recorder := serve(t, server, validQuery, slotRequest())

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", recorder.Code, recorder.Body.String())
	}
	response := decodeResponse(t, recorder)
	if len(response.Bid) != 1 {
		t.Fatalf("got %d bids, want 1", len(response.Bid))
	}
	bid := response.Bid[0]
	if bid.Impid != "imp1" || bid.AdID != "AD1" || bid.Cid != "C1" || bid.Crid != "CR1" {
		t.Errorf("bid does not point at the ad and impression it should: %+v", bid)
	}
	if bid.Ext.Kslotid != "req1_imp1" {
		t.Errorf("kslotid = %q, want req1_imp1", bid.Ext.Kslotid)
	}
	if response.Cur != "USD" {
		t.Errorf("currency = %q, want USD", response.Cur)
	}
}

func TestAdserve_TrackingUrlsCarryTheAdIdentity(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server := newTestServer(t, store, adManager(t).URL)

	bid := decodeResponse(t, serve(t, server, validQuery, slotRequest())).Bid[0]

	for _, tracking := range []struct{ url, prefix string }{
		{bid.Ext.ClickUrl, "http://engagement/clk?iid="},
		{bid.Ext.RenderUrl, "http://engagement/csc?iid="},
	} {
		if !strings.HasPrefix(tracking.url, tracking.prefix) {
			t.Fatalf("url %q does not start with %q", tracking.url, tracking.prefix)
		}
		raw, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(tracking.url, tracking.prefix))
		if err != nil {
			t.Fatalf("iid is not base64: %v", err)
		}
		var iid cache.IIDData
		if err := json.Unmarshal(raw, &iid); err != nil {
			t.Fatalf("iid is not JSON: %v", err)
		}
		if iid.AdID != "AD1" || iid.CreativeID != "CR1" || iid.CampaignID != "C1" ||
			iid.AdvertiserID != "A1" || iid.AdUnitId != "ADU1" || iid.RequestTimeStamp == 0 {
			t.Errorf("iid has the wrong identity: %+v", iid)
		}
	}
}

func TestAdserve_BothParametersAreRequired(t *testing.T) {
	server := newTestServer(t, newFakeStore(), adManager(t).URL)
	for _, query := range []string{"", "adunit_id=ADU1", "publisher_id=P1"} {
		if code := serve(t, server, query, slotRequest()).Code; code != http.StatusBadRequest {
			t.Errorf("query %q: status = %d, want 400", query, code)
		}
	}
}

func TestAdserve_UnknownPublisherOrAdUnitIsA404(t *testing.T) {
	server := newTestServer(t, newFakeStore(), adManager(t).URL)

	recorder := serve(t, server, "adunit_id=ADU1&publisher_id=NOPE", slotRequest())
	if recorder.Code != http.StatusNotFound || !strings.Contains(recorder.Body.String(), "publisher not found") {
		t.Errorf("unknown publisher: %d %s", recorder.Code, recorder.Body.String())
	}

	recorder = serve(t, server, "adunit_id=NOPE&publisher_id=P1", slotRequest())
	if recorder.Code != http.StatusNotFound || !strings.Contains(recorder.Body.String(), "ad unit not found") {
		t.Errorf("unknown ad unit: %d %s", recorder.Code, recorder.Body.String())
	}
}

func TestAdserve_IdsAreEscapedBeforeTheyReachTheManager(t *testing.T) {
	var seen string
	manager := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = r.URL.EscapedPath()
		w.WriteHeader(http.StatusNotFound)
	}))
	defer manager.Close()
	server := newTestServer(t, newFakeStore(), manager.URL)

	serve(t, server, "adunit_id=ADU1&publisher_id=../reports", slotRequest())

	if seen != "/publisher/publisherid/..%2Freports" {
		t.Errorf("the manager saw path %q, so the id was not escaped", seen)
	}
}

func TestAdserve_ManagerDownIsA502(t *testing.T) {
	manager := adManager(t)
	url := manager.URL
	manager.Close()
	server := newTestServer(t, newFakeStore(), url)

	recorder := serve(t, server, validQuery, slotRequest())

	if recorder.Code != http.StatusBadGateway {
		t.Errorf("status = %d, want 502", recorder.Code)
	}
}

func TestAdserve_SlowManagerTimesOut(t *testing.T) {
	release := make(chan struct{})
	slow := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		<-release
	}))
	defer slow.Close()
	defer close(release)
	server := newTestServer(t, newFakeStore(), slow.URL)
	server.httpClient.Timeout = 50 * time.Millisecond

	started := time.Now()
	recorder := serve(t, server, validQuery, slotRequest())

	if recorder.Code != http.StatusBadGateway {
		t.Errorf("status = %d, want 502", recorder.Code)
	}
	if time.Since(started) > 2*time.Second {
		t.Error("the request waited far longer than the client timeout")
	}
}

func TestAdserve_ColdCacheMeansNoAdNotAnError(t *testing.T) {
	server := newTestServer(t, newFakeStore(), adManager(t).URL)

	if code := serve(t, server, validQuery, slotRequest()).Code; code != http.StatusNoContent {
		t.Errorf("status = %d, want 204 when nothing is cached yet", code)
	}
}

func TestAdserve_StoreFailureIsA500WithoutDetails(t *testing.T) {
	store := newFakeStore()
	store.getErr = errors.New("dial tcp 10.0.0.5:6379: connection refused")
	server := newTestServer(t, store, adManager(t).URL)

	recorder := serve(t, server, validQuery, slotRequest())

	if recorder.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", recorder.Code)
	}
	if strings.Contains(recorder.Body.String(), "10.0.0.5") {
		t.Errorf("the response leaks the internal error: %s", recorder.Body.String())
	}
}

func TestAdserve_NoContentWhenNothingQualifies(t *testing.T) {
	cases := map[string]func(*testing.T, *fakeStore){
		"the ad is aimed at a different ad unit": func(t *testing.T, store *fakeStore) {
			ad := liveAd("AD1", 1)
			ad.AdUnitTargeted = []string{"SOMEWHERE_ELSE"}
			seedCampaign(t, store, ad)
		},
		"the ad's flight has ended": func(t *testing.T, store *fakeStore) {
			ad := liveAd("AD1", 1)
			ad.StartDate, ad.EndDate = window(-2*time.Hour, -time.Hour)
			seedCampaign(t, store, ad)
		},
		"the campaign's flight has ended": func(t *testing.T, store *fakeStore) {
			seedCampaign(t, store, liveAd("AD1", 1))
			start, end := window(-2*time.Hour, -time.Hour)
			store.values["campaigns"] = mustJSON(t, []cache.Campaign{{CampaignID: "C1", StartDate: start, EndDate: end}})
		},
		"the campaign has a bad date": func(t *testing.T, store *fakeStore) {
			seedCampaign(t, store, liveAd("AD1", 1))
			store.values["campaigns"] = mustJSON(t, []cache.Campaign{{CampaignID: "C1", StartDate: "yesterday", EndDate: "tomorrow"}})
		},
		"the creative is not in the cache": func(t *testing.T, store *fakeStore) {
			seedCampaign(t, store, liveAd("AD1", 1))
			delete(store.values, "CR1")
		},
		"no creative fits the slot": func(t *testing.T, store *fakeStore) {
			seedCampaign(t, store, liveAd("AD1", 1))
			store.values["CR1"] = mustJSON(t, cache.Creative{
				Assets: []cache.CreativeAsset{{Type: "IMAGE", Width: 728, Height: 90}},
			})
		},
		"the campaign has no ads": func(t *testing.T, store *fakeStore) {
			seedCampaign(t, store)
		},
	}
	for name, seed := range cases {
		t.Run(name, func(t *testing.T) {
			store := newFakeStore()
			seed(t, store)
			server := newTestServer(t, store, adManager(t).URL)

			if code := serve(t, server, validQuery, slotRequest()).Code; code != http.StatusNoContent {
				t.Errorf("status = %d, want 204", code)
			}
		})
	}
}

func TestAdserve_SkipsAMalformedAdAndServesTheRest(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	store.hashes["C1"]["BROKEN"] = "{not json"
	server := newTestServer(t, store, adManager(t).URL)

	recorder := serve(t, server, validQuery, slotRequest())

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", recorder.Code)
	}
	if bids := decodeResponse(t, recorder).Bid; len(bids) != 1 || bids[0].AdID != "AD1" {
		t.Errorf("unexpected bids: %+v", bids)
	}
}

func TestAdserve_LowerPriorityNumberWinsTheSlot(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("LATE", 9), liveAd("FIRST", 1), liveAd("MIDDLE", 5))
	server := newTestServer(t, store, adManager(t).URL)

	bids := decodeResponse(t, serve(t, server, validQuery, slotRequest())).Bid

	if len(bids) != 1 || bids[0].AdID != "FIRST" {
		t.Errorf("expected only FIRST to win the single slot, got %+v", bids)
	}
}

func TestAdserve_EachImpressionGetsAtMostOneBid(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1), liveAd("AD2", 2), liveAd("AD3", 3))
	server := newTestServer(t, store, adManager(t).URL)
	body := cache.RequestBody{ID: "req1", Imp: []cache.Impression{impression("imp1", 300, 250), impression("imp2", 300, 250)}}

	bids := decodeResponse(t, serve(t, server, validQuery, body)).Bid

	if len(bids) != 2 {
		t.Fatalf("got %d bids for 2 slots, want 2", len(bids))
	}
	if bids[0].Impid == bids[1].Impid {
		t.Errorf("both bids use impression %q", bids[0].Impid)
	}
	if bids[0].AdID != "AD1" || bids[1].AdID != "AD2" {
		t.Errorf("slots should go to the best-ranked ads first: %s, %s", bids[0].AdID, bids[1].AdID)
	}
}

func TestAdserve_TrackingUrlsAreSignedWhenThereIsASecret(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server := newTestServer(t, store, adManager(t).URL)
	server.config.TrackingSecret = "test-secret"

	bid := decodeResponse(t, serve(t, server, validQuery, slotRequest())).Bid[0]

	for _, tracking := range []string{bid.Ext.ClickUrl, bid.Ext.RenderUrl} {
		parsed, err := neturl.Parse(tracking)
		if err != nil {
			t.Fatal(err)
		}
		iid := parsed.Query().Get("iid")
		sig := parsed.Query().Get("sig")
		if iid == "" || sig == "" {
			t.Fatalf("url %q is missing iid or sig", tracking)
		}
		if want := util.SignIID("test-secret", iid); sig != want {
			t.Errorf("sig = %s, want %s", sig, want)
		}
	}
}

func TestAdserve_TrackingUrlsAreUnsignedWithoutASecret(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server := newTestServer(t, store, adManager(t).URL)

	bid := decodeResponse(t, serve(t, server, validQuery, slotRequest())).Bid[0]

	if strings.Contains(bid.Ext.ClickUrl, "sig=") || strings.Contains(bid.Ext.RenderUrl, "sig=") {
		t.Errorf("urls carry a signature although no secret is set: %s %s", bid.Ext.ClickUrl, bid.Ext.RenderUrl)
	}
}
