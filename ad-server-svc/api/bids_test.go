package api

import (
	"net/http"
	"testing"

	"adserver/cache"
)

// creativeCounter counts how many times each creative is read from the cache.
type creativeCounter struct {
	*fakeStore
	reads map[string]int
}

func (c *creativeCounter) GetCreatives(id string) (*cache.Creative, error) {
	c.reads[id]++
	return c.fakeStore.GetCreatives(id)
}

func newCreativeCounter() *creativeCounter {
	return &creativeCounter{fakeStore: newFakeStore(), reads: map[string]int{}}
}

func TestGetBids_StopsReadingCreativesOnceEveryImpressionHasABid(t *testing.T) {
	store := newCreativeCounter()
	ads := []cache.Ad{}
	for i := 0; i < 10; i++ {
		ads = append(ads, liveAd("AD"+string(rune('A'+i)), i))
	}
	seedCampaign(t, store.fakeStore, ads...)
	server := newTestServer(t, store, adManager(t).URL)

	recorder := serve(t, server, validQuery, slotRequest())

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", recorder.Code, recorder.Body.String())
	}
	if got := store.reads["CR1"]; got != 1 {
		t.Errorf("creative CR1 was read %d times for one impression and ten ads, want 1", got)
	}
	response := decodeResponse(t, recorder)
	if len(response.Bid) != 1 || response.Bid[0].AdID != "ADA" {
		t.Errorf("want one bid from the highest priority ad ADA, got %+v", response.Bid)
	}
}

func TestGetBids_ReadsASharedCreativeOnceEvenWhenSeveralImpressionsUseIt(t *testing.T) {
	store := newCreativeCounter()
	seedCampaign(t, store.fakeStore, liveAd("AD1", 1), liveAd("AD2", 2), liveAd("AD3", 3))
	server := newTestServer(t, store, adManager(t).URL)

	body := cache.RequestBody{ID: "req1", Imp: []cache.Impression{impression("imp1", 300, 250), impression("imp2", 300, 250)}}
	response := decodeResponse(t, serve(t, server, validQuery, body))

	if len(response.Bid) != 2 {
		t.Fatalf("want two bids, got %+v", response.Bid)
	}
	if response.Bid[0].AdID != "AD1" || response.Bid[1].AdID != "AD2" {
		t.Errorf("bids went to %s and %s, want AD1 and AD2", response.Bid[0].AdID, response.Bid[1].AdID)
	}
	if got := store.reads["CR1"]; got != 1 {
		t.Errorf("creative CR1 was read %d times, want 1", got)
	}
}

func TestGetBids_KeepsLookingWhenAnImpressionCannotBeFilled(t *testing.T) {
	store := newCreativeCounter()
	seedCampaign(t, store.fakeStore, liveAd("AD1", 1), liveAd("AD2", 2))
	server := newTestServer(t, store, adManager(t).URL)

	// imp2 asks for a size no creative has, so the walk must go through every ad before giving up on it
	body := cache.RequestBody{ID: "req1", Imp: []cache.Impression{impression("imp1", 300, 250), impression("imp2", 728, 90)}}
	response := decodeResponse(t, serve(t, server, validQuery, body))

	if len(response.Bid) != 1 || response.Bid[0].Impid != "imp1" {
		t.Fatalf("want one bid for imp1, got %+v", response.Bid)
	}
	if got := store.reads["CR1"]; got != 1 {
		t.Errorf("creative CR1 was read %d times, want 1", got)
	}
}

func TestGetBids_ImpressionsSharingAnIDGetOneBid(t *testing.T) {
	store := newCreativeCounter()
	seedCampaign(t, store.fakeStore, liveAd("AD1", 1), liveAd("AD2", 2))
	server := newTestServer(t, store, adManager(t).URL)

	body := cache.RequestBody{ID: "req1", Imp: []cache.Impression{impression("same", 300, 250), impression("same", 300, 250)}}
	response := decodeResponse(t, serve(t, server, validQuery, body))

	if len(response.Bid) != 1 {
		t.Fatalf("want one bid for two impressions with the same id, got %d", len(response.Bid))
	}
}

func TestGetBids_AnUnreadableCreativeIsSkippedForEveryAdThatUsesIt(t *testing.T) {
	store := newCreativeCounter()
	broken := liveAd("AD1", 1)
	broken.CreativeID = "BROKEN"
	broken2 := liveAd("AD2", 2)
	broken2.CreativeID = "BROKEN"
	seedCampaign(t, store.fakeStore, broken, broken2, liveAd("AD3", 3))
	store.values["BROKEN"] = "{not json"
	server := newTestServer(t, store, adManager(t).URL)

	response := decodeResponse(t, serve(t, server, validQuery, slotRequest()))

	if len(response.Bid) != 1 || response.Bid[0].AdID != "AD3" {
		t.Fatalf("want the one readable ad AD3 to win, got %+v", response.Bid)
	}
	if got := store.reads["BROKEN"]; got != 1 {
		t.Errorf("the unreadable creative was read %d times, want 1", got)
	}
}

func TestDistinctImpressionIDs(t *testing.T) {
	cases := []struct {
		name string
		imps []cache.Impression
		want int
	}{
		{"none", nil, 0},
		{"two different", []cache.Impression{{ID: "a"}, {ID: "b"}}, 2},
		{"two the same", []cache.Impression{{ID: "a"}, {ID: "a"}}, 1},
		{"empty id counts once", []cache.Impression{{ID: ""}, {ID: ""}, {ID: "a"}}, 2},
	}
	for _, c := range cases {
		if got := distinctImpressionIDs(c.imps); got != c.want {
			t.Errorf("%s: got %d, want %d", c.name, got, c.want)
		}
	}
}
