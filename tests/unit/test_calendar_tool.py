"""Tests for deterministic U.S. federal-holiday calculations."""

from datetime import date

from app.tools import check_us_federal_holiday


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
