package cache

import (
	"encoding/json"
	"testing"
	"time"
)

func TestFlight_ADecodedAdHasItsDatesParsedOnce(t *testing.T) {
	var ad Ad
	if err := json.Unmarshal([]byte(`{"adid":"AD1","startdate":"2026-11-01T00:00:00","enddate":"2026-11-30T12:30:00.250000"}`), &ad); err != nil {
		t.Fatal(err)
	}
	if ad.flight == nil {
		t.Fatal("decoding did not parse the dates")
	}
	start, end, err := ad.Flight()
	if err != nil || !start.Equal(time.Date(2026, 11, 1, 0, 0, 0, 0, time.UTC)) ||
		!end.Equal(time.Date(2026, 11, 30, 12, 30, 0, 250_000_000, time.UTC)) {
		t.Errorf("got %v, %v, %v", start, end, err)
	}
}

func TestFlight_AnAdBuiltInCodeIsParsedWhenAsked(t *testing.T) {
	ad := Ad{StartDate: "2026-11-01T00:00:00", EndDate: "2026-11-02T00:00:00"}
	start, end, err := ad.Flight()
	if err != nil || end.Sub(start) != 24*time.Hour {
		t.Errorf("got %v, %v, %v", start, end, err)
	}
}

func TestFlight_ABadDateIsAnError(t *testing.T) {
	for _, raw := range []string{
		`{"startdate":"yesterday","enddate":"2026-11-02T00:00:00"}`,
		`{"startdate":"2026-11-01T00:00:00","enddate":""}`,
	} {
		var ad Ad
		if err := json.Unmarshal([]byte(raw), &ad); err != nil {
			t.Fatalf("a bad date must not stop the ad decoding: %v", err)
		}
		if _, _, err := ad.Flight(); err == nil {
			t.Errorf("%s: want an error", raw)
		}
	}
}

func TestFlight_TheParsedDatesStayOutOfTheJSON(t *testing.T) {
	var ad Ad
	if err := json.Unmarshal([]byte(`{"adid":"AD1","startdate":"2026-11-01T00:00:00","enddate":"2026-11-02T00:00:00"}`), &ad); err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(ad)
	if err != nil {
		t.Fatal(err)
	}
	var back Ad
	if err := json.Unmarshal(raw, &back); err != nil || back.AdID != "AD1" || back.StartDate != ad.StartDate {
		t.Errorf("round trip gave %+v, %v", back, err)
	}
}
