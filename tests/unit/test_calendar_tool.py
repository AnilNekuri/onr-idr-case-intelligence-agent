"""Tests for deterministic U.S. federal-holiday calculations."""

from datetime import date

import pytest

from app.tools import add_us_federal_business_days, check_us_federal_holiday


def test_regular_date_is_not_a_federal_holiday() -> None:
    assert check_us_federal_holiday(date(2026, 8, 15)) == ()


def test_weekend_holiday_and_observed_weekday_are_both_reported() -> None:
    observed = check_us_federal_holiday(date(2026, 7, 3))
    actual = check_us_federal_holiday(date(2026, 7, 4))

    assert [(item.name, item.observed) for item in observed] == [
        ("Independence Day", True)
    ]
    assert [(item.name, item.observed) for item in actual] == [
        ("Independence Day", False)
    ]


def test_next_year_new_year_can_be_observed_in_previous_year() -> None:
    result = check_us_federal_holiday(date(2021, 12, 31))

    assert len(result) == 1
    assert result[0].name == "New Year's Day"
    assert result[0].actual_date == date(2022, 1, 1)
    assert result[0].observed


def test_thanksgiving_uses_fourth_thursday() -> None:
    result = check_us_federal_holiday(date(2026, 11, 26))

    assert len(result) == 1
    assert result[0].name == "Thanksgiving Day"


def test_add_business_days_skips_weekends_and_observed_federal_holidays() -> None:
    assert add_us_federal_business_days(date(2026, 7, 2), 1) == date(2026, 7, 6)
    assert add_us_federal_business_days(date(2026, 8, 14), 4) == date(
        2026, 8, 20
    )


def test_add_business_days_rejects_negative_offsets() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        add_us_federal_business_days(date(2026, 8, 14), -1)
