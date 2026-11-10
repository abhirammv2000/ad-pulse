package cache

import (
	"encoding/json"
	"math"
	"testing"
)

func TestMoney_ReadsAmountsExactly(t *testing.T) {
	cases := map[string]Money{
		"10":         10_000_000,
		"2.5":        2_500_000,
		"0.1":        100_000,
		"0.000001":   1,
		"1e-06":      1, // how Python's json.dumps writes 0.000001
		"1E2":        100_000_000,
		"1.5e+3":     1_500_000_000,
		"1000000000": 1_000_000_000_000_000,
		"0":          0,
		"-1.25":      -1_250_000,
	}
	for text, want := range cases {
		var got Money
		if err := json.Unmarshal([]byte(text), &got); err != nil {
			t.Errorf("%s: unexpected error %v", text, err)
			continue
		}
		if got != want {
			t.Errorf("%s: got %d micros, want %d", text, got, want)
		}
	}
}

func TestMoney_NullLeavesTheValueAlone(t *testing.T) {
	got := Money(7)
	if err := json.Unmarshal([]byte("null"), &got); err != nil || got != 7 {
		t.Errorf("got %d, %v, want 7 and no error", got, err)
	}
}

func TestMoney_RefusesWhatIsNotAnExactAmount(t *testing.T) {
	cases := []string{
		`"10"`,                // a string, which is what the old dashboard sent
		`""`,                  // an empty field from the old dashboard
		`0.0000001`,           // smaller than one micro
		`1e30`,                // exponent out of range
		`1e-30`,               // exponent out of range
		`9223372036854775807`, // too many micros for an int64
		`true`,
		`{}`,
		`[1]`,
	}
	for _, text := range cases {
		var got Money
		if err := json.Unmarshal([]byte(text), &got); err == nil {
			t.Errorf("%s: want an error, got %d micros", text, got)
		}
	}
}

func TestMoney_WritesWholeUnits(t *testing.T) {
	cases := map[Money]string{
		10_000_000:    "10",
		2_500_000:     "2.5",
		1:             "0.000001",
		0:             "0",
		-1_500_000:    "-1.5",
		math.MinInt64: "-9223372036854.775808",
	}
	for amount, want := range cases {
		raw, err := json.Marshal(amount)
		if err != nil || string(raw) != want {
			t.Errorf("%d micros: got %s, %v, want %s", int64(amount), raw, err, want)
		}
	}
}

func TestMoney_RoundTrips(t *testing.T) {
	for _, amount := range []Money{0, 1, 999_999, 1_000_000, 2_500_000, 123_456_789_012} {
		raw, err := json.Marshal(amount)
		if err != nil {
			t.Fatal(err)
		}
		var back Money
		if err := json.Unmarshal(raw, &back); err != nil || back != amount {
			t.Errorf("%d micros came back as %d (%s, %v)", int64(amount), back, raw, err)
		}
	}
}

func TestMoney_InsideAnAd(t *testing.T) {
	var ad Ad
	raw := `{"bidinfo":{"bid":2.5,"bidType":"CPM"},"budget":{"currencyCode":"USD","dailyBudget":10,"totalBudget":100.75}}`
	if err := json.Unmarshal([]byte(raw), &ad); err != nil {
		t.Fatal(err)
	}
	if ad.BidInfo.Bid != 2_500_000 || ad.Budget.DailyBudget != 10_000_000 || ad.Budget.TotalBudget != 100_750_000 {
		t.Errorf("got bid %d, daily %d, total %d", ad.BidInfo.Bid, ad.Budget.DailyBudget, ad.Budget.TotalBudget)
	}
}
