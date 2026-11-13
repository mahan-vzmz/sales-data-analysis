"""Weekly forecasting features and chronological validation folds."""

from collections.abc import Iterable, Iterator
from datetime import date
from numbers import Integral

import pandas as pd

_TARGET = "ordered_quantity"
_LAGGED_COLUMNS = [
    _TARGET,
    "promoted_order_count",
    "average_unit_price",
    "effective_discount_rate",
    "online_unit_share",
    "store_unit_share",
    "marketplace_unit_share",
]
_KNOWN_COLUMNS = ["week_start", "category", "holiday_days", "campaign_days"]


def build_forecast_features(weekly_sales: pd.DataFrame) -> pd.DataFrame:
    """Use mart_forecasting_base to build features available at each week's start.

    Ordered units are the target. Calendar and campaign schedules are known
    ahead of time. Realized sales drivers are lagged by one week. Early rows
    and weeks without observed prices retain missing features.

    For a fixed-origin multiweek forecast, build lagged features using only
    observations available at that origin and any recursive predictions.
    """
    weekly = weekly_sales[[*_KNOWN_COLUMNS, *_LAGGED_COLUMNS]].copy()
    weekly["week_start"] = pd.to_datetime(weekly["week_start"]).dt.normalize()
    if weekly[["week_start", "category", _TARGET]].isna().any().any():
        raise ValueError("week_start, category and ordered_quantity must be present")
    if weekly["week_start"].dt.dayofweek.ne(0).any():
        raise ValueError("week_start must be a Monday")
    if weekly.duplicated(["category", "week_start"]).any():
        raise ValueError("category and week_start must form a unique key")

    weekly = weekly.sort_values(["category", "week_start"], ignore_index=True)
    gaps = weekly.groupby("category")["week_start"].diff().dropna()
    if gaps.ne(pd.Timedelta(weeks=1)).any():
        raise ValueError("Weeks must be consecutive within each category")

    result = weekly[[*_KNOWN_COLUMNS, _TARGET]].copy()
    result["iso_week"] = weekly["week_start"].dt.isocalendar().week
    lags = weekly.groupby("category")[_LAGGED_COLUMNS].shift(1)
    result = result.join(lags.add_suffix("_lag_1"))
    result["ordered_quantity_rolling_mean_4"] = (
        lags[_TARGET]
        .groupby(weekly["category"])
        .transform(lambda history: history.rolling(4).mean())
    )
    return result


def rolling_origin_splits(
    dates: Iterable[date | str], min_train: int, horizon: int, step: int
) -> Iterator[tuple[list[int], list[int]]]:
    """Yield row positions for expanding folds sized by distinct dates.

    Duplicate dates stay together and positions follow the input row order.
    Only full test windows are yielded.
    """
    if any(
        not isinstance(size, Integral) or isinstance(size, bool) or size < 1
        for size in (min_train, horizon, step)
    ):
        raise ValueError("min_train, horizon and step must be positive integers")
    min_train, horizon, step = int(min_train), int(horizon), int(step)

    row_dates = pd.DatetimeIndex(list(dates)).normalize()
    if row_dates.hasnans:
        raise ValueError("dates must be present")
    timeline = row_dates.unique().sort_values()
    for end in range(min_train, len(timeline) - horizon + 1, step):
        test_start = timeline[end]
        test_end = timeline[end + horizon - 1]
        train = (row_dates < test_start).nonzero()[0].tolist()
        test = (
            ((row_dates >= test_start) & (row_dates <= test_end)).nonzero()[0].tolist()
        )
        yield train, test
