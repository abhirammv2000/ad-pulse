package cache

import (
	"fmt"
	"math/big"
	"strconv"
	"strings"
)

// microsPerUnit is how many micros make one unit of currency.
const microsPerUnit = 1_000_000

// Money is an amount in micros, so 1 USD is 1,000,000.
//
// The ad manager stores bids and budgets as JSON numbers in whole units, such as
// 2.5 for two dollars fifty. Money reads that text straight into an integer,
// never through a float, so no amount is rounded on the way in.
type Money int64

func (m *Money) UnmarshalJSON(data []byte) error {
	text := string(data)
	if text == "null" {
		return nil // same as a missing field
	}
	if text == "" || (text[0] != '-' && (text[0] < '0' || text[0] > '9')) {
		return fmt.Errorf("an amount must be a JSON number, got %s", text)
	}
	// A huge exponent would make big.Rat build a huge number. Real amounts never need one.
	if i := strings.IndexAny(text, "eE"); i >= 0 {
		exponent, err := strconv.Atoi(text[i+1:])
		if err != nil || exponent < -20 || exponent > 20 {
			return fmt.Errorf("an amount has an exponent out of range: %s", text)
		}
	}

	amount, ok := new(big.Rat).SetString(text)
	if !ok {
		return fmt.Errorf("an amount is not a number: %s", text)
	}
	amount.Mul(amount, big.NewRat(microsPerUnit, 1))
	if !amount.IsInt() {
		return fmt.Errorf("an amount can have at most 6 decimal places: %s", text)
	}
	if !amount.Num().IsInt64() {
		return fmt.Errorf("an amount is too large: %s", text)
	}
	*m = Money(amount.Num().Int64())
	return nil
}

// MarshalJSON writes the amount back in whole units, the way the ad manager stores it.
func (m Money) MarshalJSON() ([]byte, error) {
	return []byte(m.String()), nil
}

// String formats the amount in whole units, such as 2.5 or 10.
func (m Money) String() string {
	sign := ""
	micros := uint64(m)
	if m < 0 {
		sign = "-"
		micros = -micros // unsigned negation gives the size of the amount, even for the smallest int64
	}
	units, rest := micros/microsPerUnit, micros%microsPerUnit
	if rest == 0 {
		return fmt.Sprintf("%s%d", sign, units)
	}
	return strings.TrimRight(fmt.Sprintf("%s%d.%06d", sign, units, rest), "0")
}
