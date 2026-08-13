from datetime import date

import pytest

from sales_analytics.generation.patterns import calendar_dates


def test_calendar_dates_include_every_day_in_range() -> None:
    dates = calendar_dates(date(2024, 2, 28), date(2024, 3, 1))

    assert dates == (
        date(2024, 2, 28),
        date(2024, 2, 29),
        date(2024, 3, 1),
    )


def test_calendar_dates_reject_reversed_range() -> None:
    with pytest.raises(ValueError, match="start_date"):
        calendar_dates(date(2025, 1, 2), date(2025, 1, 1))
