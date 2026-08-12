"""Small deterministic building blocks for generated patterns."""

from datetime import date, timedelta
from random import Random


def calendar_dates(start_date: date, end_date: date) -> tuple[date, ...]:
    """Return every calendar date in an inclusive range."""
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")

    return tuple(
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    )


def weighted_order_date(
    random: Random,
    year: int,
    peak_months: tuple[int, ...],
    peak_weight: float,
    promotion_weight: float,
    promotion_window: tuple[tuple[int, int], tuple[int, int]],
) -> date:
    """Choose a date with explicit seasonal and promotion weights."""
    dates = calendar_dates(date(year, 1, 1), date(year, 12, 31))
    weights = []
    promotion_start, promotion_end = promotion_dates(year, promotion_window)
    for candidate in dates:
        weight = peak_weight if candidate.month in peak_months else 1.0
        if promotion_start <= candidate <= promotion_end:
            weight *= promotion_weight
        weights.append(weight)

    return random.choices(dates, weights=weights, k=1)[0]


def promotion_dates(
    year: int, window: tuple[tuple[int, int], tuple[int, int]]
) -> tuple[date, date]:
    """Convert configured month/day pairs into dates for one year."""
    start, end = window
    return date(year, *start), date(year, *end)
