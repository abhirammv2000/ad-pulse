package api

import (
	"fmt"
	"reflect"
	"sync"
	"testing"
	"time"

	"adserver/cache"
)

type pair struct {
	Name  string `json:"name"`
	Items []int  `json:"items"`
}

func TestContentCache_DecodesLikeJSONAndRemembersTheResult(t *testing.T) {
	c := newContentCache[pair](4)
	raw := `{"name":"a","items":[1,2,3]}`

	first, err := c.get(raw)
	if err != nil {
		t.Fatal(err)
	}
	second, err := c.get(raw)
	if err != nil {
		t.Fatal(err)
	}

	want := pair{Name: "a", Items: []int{1, 2, 3}}
	if !reflect.DeepEqual(first, want) || !reflect.DeepEqual(second, want) {
		t.Errorf("got %+v and %+v, want %+v", first, second, want)
	}
	if c.hits.Load() != 1 || c.misses.Load() != 1 {
		t.Errorf("hits=%d misses=%d, want 1 and 1", c.hits.Load(), c.misses.Load())
	}
}

func TestContentCache_ChangedTextIsAMissNotAStaleHit(t *testing.T) {
	c := newContentCache[pair](4)
	old, _ := c.get(`{"name":"old"}`)
	fresh, _ := c.get(`{"name":"new"}`)

	if old.Name != "old" || fresh.Name != "new" {
		t.Errorf("got %q and %q", old.Name, fresh.Name)
	}
	if c.misses.Load() != 2 {
		t.Errorf("misses = %d, want 2", c.misses.Load())
	}
}

func TestContentCache_BadJSONIsAnErrorEveryTimeAndIsNotStored(t *testing.T) {
	c := newContentCache[pair](4)
	for i := 0; i < 3; i++ {
		if _, err := c.get(`{"name":`); err == nil {
			t.Fatal("want an error for truncated JSON")
		}
	}
	if c.size() != 0 {
		t.Errorf("size = %d, want 0", c.size())
	}
	if c.hits.Load() != 0 {
		t.Errorf("hits = %d, want 0", c.hits.Load())
	}
}

func TestContentCache_StaysBoundedAndKeepsWhatIsStillUsed(t *testing.T) {
	const limit = 4
	c := newContentCache[pair](limit)
	hot := `{"name":"hot"}`

	for i := 0; i < 100; i++ {
		if _, err := c.get(hot); err != nil { // touched every round, so it must survive every swap
			t.Fatal(err)
		}
		if _, err := c.get(fmt.Sprintf(`{"name":"cold%d"}`, i)); err != nil {
			t.Fatal(err)
		}
		if c.size() > 2*limit {
			t.Fatalf("size grew to %d with limit %d", c.size(), limit)
		}
	}
	if c.misses.Load() > 101 {
		t.Errorf("the hot entry was decoded again: %d misses for 101 distinct strings", c.misses.Load())
	}
}

func TestContentCache_ManyGoroutinesAgreeOnTheAnswer(t *testing.T) {
	c := newContentCache[pair](16) // small, so generations rotate while goroutines are reading
	var wg sync.WaitGroup
	for g := 0; g < 8; g++ {
		wg.Add(1)
		go func(g int) {
			defer wg.Done()
			for i := 0; i < 2000; i++ {
				n := (i*7 + g) % 40
				got, err := c.get(fmt.Sprintf(`{"name":"n%d","items":[%d]}`, n, n))
				if err != nil || got.Name != fmt.Sprintf("n%d", n) || len(got.Items) != 1 || got.Items[0] != n {
					t.Errorf("goroutine %d got %+v, %v for n=%d", g, got, err, n)
					return
				}
			}
		}(g)
	}
	wg.Wait()
}

func TestContentCache_ACopyOfAStructCannotChangeTheCachedOne(t *testing.T) {
	c := newContentCache[cache.Ad](4)
	raw := `{"adid":"AD1","adpriority":3}`
	first, _ := c.get(raw)
	first.AdID = "changed"
	first.AdPriority = 99

	second, _ := c.get(raw)
	if second.AdID != "AD1" || second.AdPriority != 3 {
		t.Errorf("the cached ad changed: %+v", second)
	}
}

func TestAdserve_ServesTheSameBidsWithAndWithoutWarmCaches(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 2), liveAd("AD2", 1))
	server := newTestServer(t, store, adManager(t).URL)

	cold := decodeResponse(t, serve(t, server, validQuery, slotRequest()))
	warm := decodeResponse(t, serve(t, server, validQuery, slotRequest()))

	if len(cold.Bid) != 1 || len(warm.Bid) != 1 || cold.Bid[0].AdID != "AD2" || warm.Bid[0].AdID != "AD2" {
		t.Fatalf("cold %+v, warm %+v", cold.Bid, warm.Bid)
	}
	if server.adsDecoded.hits.Load() < 2 {
		t.Errorf("the second request did not use the ad cache: hits=%d", server.adsDecoded.hits.Load())
	}
}

func TestAdserve_AnEditedAdIsServedAtOnceNotFromTheCache(t *testing.T) {
	store := newFakeStore()
	seedCampaign(t, store, liveAd("AD1", 1))
	server := newTestServer(t, store, adManager(t).URL)
	if first := decodeResponse(t, serve(t, server, validQuery, slotRequest())); len(first.Bid) != 1 {
		t.Fatalf("want a bid, got %+v", first.Bid)
	}

	// the refresh service rewrites the ad so that it ended an hour ago
	ended := liveAd("AD1", 1)
	ended.StartDate, ended.EndDate = window(-2*time.Hour, -time.Hour)
	store.hashes["C1"]["AD1"] = mustJSON(t, ended)

	recorder := serve(t, server, validQuery, slotRequest())
	if recorder.Code != 204 {
		t.Errorf("status = %d, want 204 because the edited ad is no longer live", recorder.Code)
	}
}
