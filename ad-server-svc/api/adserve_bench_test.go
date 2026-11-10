package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"

	"adserver/cache"
	"adserver/util"

	"github.com/gin-gonic/gin"
)

func init() {
	gin.DefaultWriter = io.Discard // gin.Default() logs every request, which would drown the benchmark output
}

// latencyStore wraps a store and sleeps before every call, the way a network round trip to Redis does. Without it a
// benchmark of an in-memory fake hides what matters most about the serve path: how many round trips one request makes.
type latencyStore struct {
	cache.Store
	delay time.Duration
	calls *callCounter
}

type callCounter struct {
	mu sync.Mutex
	n  int
}

func (c *callCounter) add() {
	c.mu.Lock()
	c.n++
	c.mu.Unlock()
}

func (l latencyStore) wait() {
	l.calls.add()
	if l.delay > 0 {
		time.Sleep(l.delay)
	}
}

func (l latencyStore) Get(key string) (string, error) { l.wait(); return l.Store.Get(key) }
func (l latencyStore) Set(key, value string) error    { l.wait(); return l.Store.Set(key, value) }
func (l latencyStore) HGetAll(key string) (map[string]string, error) {
	l.wait()
	return l.Store.HGetAll(key)
}
func (l latencyStore) GetCreatives(id string) (*cache.Creative, error) {
	l.wait()
	return l.Store.GetCreatives(id)
}
func (l latencyStore) MGet(keys []string) ([]string, error) {
	l.wait()
	return l.Store.MGet(keys)
}
func (l latencyStore) CountSince(queries []cache.CountQuery) ([]int64, error) {
	l.wait()
	return l.Store.CountSince(queries)
}

// benchWorld builds a cache with the given number of live campaigns, each holding adsPerCampaign ads that all use the
// same 300x250 creative, and returns a server whose manager lookups are already remembered. With a budget, every ad
// has that daily and total budget and a little spend recorded, so every request reads spend for all of them.
func benchWorld(tb testing.TB, campaigns, adsPerCampaign int, delay time.Duration, budget cache.Money) (*Server, *callCounter) {
	tb.Helper()
	store := newFakeStore()
	start, end := window(-time.Hour, time.Hour)
	list := make([]cache.Campaign, campaigns)
	for c := range list {
		id := fmt.Sprintf("C%d", c)
		list[c] = cache.Campaign{CampaignID: id, StartDate: start, EndDate: end}
		store.hashes[id] = map[string]string{}
		for a := 0; a < adsPerCampaign; a++ {
			ad := cache.Ad{
				AdID: fmt.Sprintf("%s-AD%d", id, a), CampaignID: id, AdvertiserID: "A1", CreativeID: "CR1",
				StartDate: start, EndDate: end, AdPriority: a % 7, LandingURL: "http://landing",
			}
			if budget > 0 {
				ad.Budget.DailyBudget, ad.Budget.TotalBudget = budget, budget
				store.values[spendKey("ad", ad.AdID)] = "1000"
				store.values[dailySpendKey("ad", ad.AdID, time.Now().UTC().Format("2006-01-02"))] = "1000"
			}
			raw, err := json.Marshal(ad)
			if err != nil {
				tb.Fatal(err)
			}
			store.hashes[id][ad.AdID] = string(raw)
		}
	}
	rawList, err := json.Marshal(list)
	if err != nil {
		tb.Fatal(err)
	}
	store.values["campaigns"] = string(rawList)
	rawCreative, err := json.Marshal(cache.Creative{
		Assets: []cache.CreativeAsset{{Type: "IMAGE", Width: 300, Height: 250, ImageURL: "http://img/1.png"}},
	})
	if err != nil {
		tb.Fatal(err)
	}
	store.values["CR1"] = string(rawCreative)

	counter := &callCounter{}
	server, err := NewServer(util.Config{ClickUrl: "http://engagement/clk", RenderUrl: "http://engagement/csc", TrackingSecret: "bench"},
		latencyStore{Store: store, delay: delay, calls: counter})
	if err != nil {
		tb.Fatal(err)
	}
	server.known.remember("/publisher/publisherid/P1")
	server.known.remember("/adunit/ad_unit_id/ADU1")
	return server, counter
}

func benchRequestBody(tb testing.TB) []byte {
	tb.Helper()
	raw, err := json.Marshal(slotRequest())
	if err != nil {
		tb.Fatal(err)
	}
	return raw
}

func serveOnce(server *Server, body []byte) int {
	request := httptest.NewRequest(http.MethodPost, "/adserve?"+validQuery, bytes.NewReader(body))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()
	server.router.ServeHTTP(recorder, request)
	return recorder.Code
}

// BenchmarkAdserve is the whole serve path with no network delay: the CPU cost of one request.
func BenchmarkAdserve(b *testing.B) {
	for _, size := range []struct{ campaigns, ads int }{{1, 10}, {10, 20}, {50, 20}} {
		b.Run(fmt.Sprintf("%dcampaigns_x_%dads", size.campaigns, size.ads), func(b *testing.B) {
			server, _ := benchWorld(b, size.campaigns, size.ads, 0, 0)
			body := benchRequestBody(b)
			if code := serveOnce(server, body); code != http.StatusOK {
				b.Fatalf("status %d", code)
			}
			b.ReportAllocs()
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				serveOnce(server, body)
			}
		})
	}
}

// BenchmarkAdserveWithBudgets is the 50 x 20 case with a budget on every ad, the most spend there is to read and
// check. Compare it with BenchmarkAdserve/50campaigns_x_20ads and BenchmarkAdserveRoundTrips/50campaigns.
func BenchmarkAdserveWithBudgets(b *testing.B) {
	for _, run := range []struct {
		name  string
		delay time.Duration
	}{{"cpu", 0}, {"round_trips", 200 * time.Microsecond}} {
		b.Run(run.name, func(b *testing.B) {
			server, counter := benchWorld(b, 50, 20, run.delay, 1000*dollar)
			body := benchRequestBody(b)
			if code := serveOnce(server, body); code != http.StatusOK {
				b.Fatalf("status %d", code)
			}
			counter.n = 0
			b.ReportAllocs()
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				serveOnce(server, body)
			}
			b.ReportMetric(float64(counter.n)/float64(b.N), "cache_calls/op")
		})
	}
}

// BenchmarkAdserveParallel runs requests from all cores at once, which is where a shared lock would show.
func BenchmarkAdserveParallel(b *testing.B) {
	server, _ := benchWorld(b, 10, 20, 0, 0)
	body := benchRequestBody(b)
	b.ReportAllocs()
	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			serveOnce(server, body)
		}
	})
}

// BenchmarkAdserveRoundTrips charges 200 microseconds for every cache call, a typical same-zone Redis round trip, and
// reports how many calls one request makes. This is the number that grows with the campaign count.
func BenchmarkAdserveRoundTrips(b *testing.B) {
	for _, campaigns := range []int{1, 10, 50} {
		b.Run(fmt.Sprintf("%dcampaigns", campaigns), func(b *testing.B) {
			server, counter := benchWorld(b, campaigns, 20, 200*time.Microsecond, 0)
			body := benchRequestBody(b)
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				serveOnce(server, body)
			}
			b.ReportMetric(float64(counter.n)/float64(b.N), "cache_calls/op")
		})
	}
}

func BenchmarkIsAdAvailable(b *testing.B) {
	start, end := window(-time.Hour, time.Hour)
	ad := cache.Ad{AdID: "AD", StartDate: start, EndDate: end}
	params := cache.RequestParams{AdUnitId: "ADU1", PublisherId: "P1"}
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		util.IsAdAvailable(ad, params)
	}
}

// BenchmarkKnownEntitiesParallel checks that the lookup cache in front of every request is not a bottleneck when all
// cores hit it together.
func BenchmarkKnownEntitiesParallel(b *testing.B) {
	known := newKnownEntities()
	known.remember("/publisher/publisherid/P1")
	b.ReportAllocs()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			known.has("/publisher/publisherid/P1")
		}
	})
}
