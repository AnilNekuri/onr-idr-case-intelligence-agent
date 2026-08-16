"""Deterministic application-date and U.S. federal-holiday calculations."""

from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class FederalHolidayOccurrence:
    """One actual or observed occurrence of a U.S. federal holiday."""

    name: str
    date: Date
    observed: bool
    actual_date: Date

    def model_dump(self) -> dict[str, object]:
        """Return a JSON-compatible representation for a model tool result."""
        return {
            "name": self.name,
            "date": self.date.isoformat(),
            "observed": self.observed,
            "actual_date": self.actual_date.isoformat(),
        }


def check_us_federal_holiday(value: Date) -> tuple[FederalHolidayOccurrence, ...]:
    """Return federal-holiday occurrences matching one calendar date."""
    occurrences = (
        occurrence
        for year in (value.year - 1, value.year, value.year + 1)
        for occurrence in _federal_holidays(year)
    )
    return tuple(
        sorted(
            (occurrence for occurrence in occurrences if occurrence.date == value),
            key=lambda occurrence: (occurrence.name, occurrence.observed),
        )
    )


def is_us_federal_business_day(value: Date) -> bool:
    """Return whether a date is Monday-Friday and not a Federal holiday."""
    return value.weekday() < 5 and not check_us_federal_holiday(value)


def add_us_federal_business_days(value: Date, days: int) -> Date:
    """Add business days, excluding the starting date from the count."""
    if days < 0:
        raise ValueError("days must be non-negative")
    current = value
    remaining = days
    while remaining:
        current += timedelta(days=1)
        if is_us_federal_business_day(current):
            remaining -= 1
    return current


def _federal_holidays(year: int) -> tuple[FederalHolidayOccurrence, ...]:
    actual_holidays = (
        ("New Year's Day", Date(year, 1, 1)),
        ("Birthday of Martin Luther King, Jr.", _nth_weekday(year, 1, 0, 3)),
        ("Washington's Birthday", _nth_weekday(year, 2, 0, 3)),
        ("Memorial Day", _last_weekday(year, 5, 0)),
        ("Juneteenth National Independence Day", Date(year, 6, 19)),
        ("Independence Day", Date(year, 7, 4)),
        ("Labor Day", _nth_weekday(year, 9, 0, 1)),
        ("Columbus Day", _nth_weekday(year, 10, 0, 2)),
        ("Veterans Day", Date(year, 11, 11)),
        ("Thanksgiving Day", _nth_weekday(year, 11, 3, 4)),
        ("Christmas Day", Date(year, 12, 25)),
    )
    occurrences: list[FederalHolidayOccurrence] = []
    for name, actual_date in actual_holidays:
        occurrences.append(
            FederalHolidayOccurrence(name, actual_date, False, actual_date)
        )
        observed_date = _observed_date(actual_date)
        if observed_date != actual_date:
            occurrences.append(
                FederalHolidayOccurrence(name, observed_date, True, actual_date)
            )
    return tuple(occurrences)


def _observed_date(value: Date) -> Date:
    if value.weekday() == 5:
        return value - timedelta(days=1)
    if value.weekday() == 6:
        return value + timedelta(days=1)
    return value


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> Date:
    first = Date(year, month, 1)
    offset = (weekday - first.weekday()) % 7 + 7 * (occurrence - 1)
    return first + timedelta(days=offset)


def _last_weekday(year: int, month: int, weekday: int) -> Date:
    next_month = Date(year + (month == 12), month % 12 + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)
