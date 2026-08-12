"""Small deterministic building blocks for generated patterns."""

from datetime import date, timedelta


def calendar_dates(start_date: date, end_date: date) -> tuple[date, ...]:
    """Return every calendar date in an inclusive range."""
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")

    return tuple(
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    )
