"""Tests for app/validation.py. Pure functions, so no database or app."""

import copy
import unittest

from app.validation import ValidationError, validate_ad, validate_campaign

# The ad the end-to-end test creates, which has to stay valid.
GOOD_AD = {
    "ad_unit_targeted": ["ADU1"],
    "adname": "Integration Test Ad",
    "adpriority": 8,
    "bidinfo": {"bid": 1, "bidType": "CPM"},
    "budget": {"currencyCode": "USD", "dailyBudget": 10, "totalBudget": 10},
    "frequencycaps": {
        "frequencyCapList": [
            {
                "entityType": "AD",
                "eventType": "CSC",
                "timeFrame": {"maxCount": 3, "timeWindowType": "DAY", "value": 1},
                "userCap": True,
            }
        ]
    },
    "targetinginfo": {
        "dayTargeting": {"type": "equal", "values": [1, 7]},
        "timeTargeting": {"type": "equal", "values": [0, 23]},
    },
}


def ad_with(**changes):
    ad = copy.deepcopy(GOOD_AD)
    ad.update(changes)
    return ad


class ValidAdTest(unittest.TestCase):
    def test_the_end_to_end_ad_is_valid(self):
        validate_ad(GOOD_AD)

    def test_an_ad_with_none_of_the_json_fields_is_valid(self):
        validate_ad({"adname": "plain"})

    def test_null_means_not_set(self):
        validate_ad({field: None for field in ("bidinfo", "budget", "ad_unit_targeted", "targetinginfo", "frequencycaps")})

    def test_decimal_amounts_up_to_six_places(self):
        validate_ad(ad_with(bidinfo={"bid": 2.5, "bidType": "CPC"}, budget={"dailyBudget": 0.000001}))

    def test_an_empty_ad_unit_list_means_every_ad_unit(self):
        validate_ad(ad_with(ad_unit_targeted=[]))

    def test_rules_and_cap_lists_left_empty_are_valid(self):
        validate_ad(ad_with(targetinginfo={"dayTargeting": {"type": "equal"}}, frequencycaps={}))
        validate_ad(ad_with(frequencycaps={"frequencyCapList": None}))


class InvalidAdTest(unittest.TestCase):
    def assert_rejected(self, ad, field):
        with self.assertRaises(ValidationError) as caught:
            validate_ad(ad)
        self.assertEqual(caught.exception.field, field)

    def test_amounts_sent_as_strings_are_rejected(self):
        # What the dashboard used to send. The ad server cannot read it and skips the ad.
        self.assert_rejected(ad_with(bidinfo={"bid": "2", "bidType": "CPM"}), "bidinfo.bid")
        self.assert_rejected(ad_with(budget={"dailyBudget": ""}), "budget.dailyBudget")

    def test_amounts_must_be_more_than_zero(self):
        self.assert_rejected(ad_with(bidinfo={"bid": 0, "bidType": "CPM"}), "bidinfo.bid")
        self.assert_rejected(ad_with(budget={"totalBudget": -5}), "budget.totalBudget")

    def test_amounts_have_at_most_six_decimal_places(self):
        self.assert_rejected(ad_with(budget={"dailyBudget": 0.0000001}), "budget.dailyBudget")
        self.assert_rejected(ad_with(budget={"dailyBudget": 0.1 + 0.2}), "budget.dailyBudget")

    def test_amounts_have_a_ceiling(self):
        self.assert_rejected(ad_with(budget={"totalBudget": 10**12}), "budget.totalBudget")

    def test_amounts_that_are_not_finite_or_not_numbers(self):
        for bad in (float("nan"), float("inf"), True, [1], {"value": 1}):
            self.assert_rejected(ad_with(bidinfo={"bid": bad, "bidType": "CPM"}), "bidinfo.bid")

    def test_bid_needs_both_parts(self):
        self.assert_rejected(ad_with(bidinfo={"bid": 1}), "bidinfo.bidType")
        self.assert_rejected(ad_with(bidinfo={"bidType": "CPM"}), "bidinfo.bid")

    def test_cpd_is_not_a_bid_type(self):
        self.assert_rejected(ad_with(bidinfo={"bid": 1, "bidType": "CPD"}), "bidinfo.bidType")

    def test_only_usd(self):
        self.assert_rejected(ad_with(budget={"dailyBudget": 1, "currencyCode": "INR"}), "budget.currencyCode")

    def test_lowercase_keys_from_the_old_dashboard_are_rejected(self):
        self.assert_rejected(ad_with(budget={"dailybudget": 10}), "budget.dailybudget")
        self.assert_rejected(ad_with(bidinfo={"bid": 1, "bidtype": "CPM"}), "bidinfo.bidtype")

    def test_json_fields_must_have_the_right_shape(self):
        self.assert_rejected(ad_with(bidinfo=[1, "CPM"]), "bidinfo")
        self.assert_rejected(ad_with(budget="10"), "budget")
        self.assert_rejected(ad_with(targetinginfo=[]), "targetinginfo")

    def test_ad_units_are_a_flat_list_of_ids(self):
        # The old dashboard sent [[]] when no ad unit was picked.
        self.assert_rejected(ad_with(ad_unit_targeted=[[]]), "ad_unit_targeted[0]")
        self.assert_rejected(ad_with(ad_unit_targeted="ADU1"), "ad_unit_targeted")
        self.assert_rejected(ad_with(ad_unit_targeted=[""]), "ad_unit_targeted[0]")

    def test_hours_are_0_to_23(self):
        self.assert_rejected(
            ad_with(targetinginfo={"timeTargeting": {"type": "equal", "values": [24]}}),
            "targetinginfo.timeTargeting.values[0]",
        )

    def test_days_are_1_to_7(self):
        self.assert_rejected(
            ad_with(targetinginfo={"dayTargeting": {"values": [3, 0]}}),
            "targetinginfo.dayTargeting.values[1]",
        )

    def test_targeting_values_are_whole_numbers(self):
        self.assert_rejected(
            ad_with(targetinginfo={"timeTargeting": {"values": ["9"]}}),
            "targetinginfo.timeTargeting.values[0]",
        )
        self.assert_rejected(
            ad_with(targetinginfo={"timeTargeting": {"values": [9.0]}}),
            "targetinginfo.timeTargeting.values[0]",
        )

    def test_targeting_type_is_equal(self):
        self.assert_rejected(
            ad_with(targetinginfo={"dayTargeting": {"type": "range", "values": [1]}}),
            "targetinginfo.dayTargeting.type",
        )


class FrequencyCapTest(unittest.TestCase):
    def cap(self, **changes):
        cap = copy.deepcopy(GOOD_AD["frequencycaps"]["frequencyCapList"][0])
        cap.update(changes)
        return ad_with(frequencycaps={"frequencyCapList": [cap]})

    def frame(self, **changes):
        frame = dict(GOOD_AD["frequencycaps"]["frequencyCapList"][0]["timeFrame"], **changes)
        return self.cap(timeFrame=frame)

    def assert_rejected(self, ad, field):
        with self.assertRaises(ValidationError) as caught:
            validate_ad(ad)
        self.assertEqual(caught.exception.field, "frequencycaps.frequencyCapList[0]" + field)

    def test_a_count_of_zero_is_rejected(self):
        # The end-to-end test used to send this placeholder, which would mean "never serve".
        self.assert_rejected(self.frame(maxCount=0, value=0), ".timeFrame.maxCount")

    def test_a_count_above_what_the_subscriber_keeps_is_rejected(self):
        validate_ad(self.frame(maxCount=1000))
        self.assert_rejected(self.frame(maxCount=1001), ".timeFrame.maxCount")

    def test_only_caps_per_user(self):
        self.assert_rejected(self.cap(userCap=False), ".userCap")

    def test_known_entities_events_and_windows(self):
        self.assert_rejected(self.cap(entityType="ADVERTISER"), ".entityType")
        self.assert_rejected(self.cap(eventType="VIEW"), ".eventType")
        self.assert_rejected(self.frame(timeWindowType="MONTH"), ".timeFrame.timeWindowType")

    def test_the_window_is_at_most_a_week(self):
        validate_ad(self.frame(value=7, timeWindowType="DAY"))
        validate_ad(self.frame(value=168, timeWindowType="HOUR"))
        self.assert_rejected(self.frame(value=8, timeWindowType="DAY"), ".timeFrame.value")
        self.assert_rejected(self.frame(value=2, timeWindowType="WEEK"), ".timeFrame.value")

    def test_every_part_is_required(self):
        self.assert_rejected(self.cap(timeFrame={"maxCount": 1, "value": 1}), ".timeFrame.timeWindowType")
        cap = copy.deepcopy(GOOD_AD["frequencycaps"]["frequencyCapList"][0])
        del cap["eventType"]
        self.assert_rejected(ad_with(frequencycaps={"frequencyCapList": [cap]}), ".eventType")

    def test_at_most_five_caps(self):
        cap = GOOD_AD["frequencycaps"]["frequencyCapList"][0]
        with self.assertRaises(ValidationError) as caught:
            validate_ad(ad_with(frequencycaps={"frequencyCapList": [cap] * 6}))
        self.assertEqual(caught.exception.field, "frequencycaps.frequencyCapList")


class CampaignTest(unittest.TestCase):
    def test_the_end_to_end_campaign_is_valid(self):
        validate_campaign({
            "campaignname": "Integration Test Campaign",
            "budget": {"currencyCode": "USD", "dailyBudget": 10, "totalBudget": 10},
        })

    def test_a_string_budget_is_rejected(self):
        # One campaign like this used to stop every ad request with a 500.
        with self.assertRaises(ValidationError) as caught:
            validate_campaign({"budget": {"dailyBudget": "10"}})
        self.assertEqual(caught.exception.field, "budget.dailyBudget")


if __name__ == '__main__':
    unittest.main()
