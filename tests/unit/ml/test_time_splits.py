from datetime import date

import numpy as np
import pandas as pd
import pytest

from sales_analytics.ml.features import rolling_origin_splits


def test_expanding_folds_keep_all_rows_for_each_week_together() -> None:
    weeks = list(pd.date_range("2025-01-06", periods=7, freq="W-MON"))
    dates = pd.DatetimeIndex(weeks + weeks)
    folds = list(rolling_origin_splits(dates, min_train=2, horizon=2, step=2))

    assert len(folds) == 2
    assert list(folds[0][0]) == [0, 1, 7, 8]
    assert list(folds[0][1]) == [2, 3, 9, 10]
    assert list(folds[1][0]) == [0, 1, 2, 3, 7, 8, 9, 10]
    assert list(folds[1][1]) == [4, 5, 11, 12]
    for train, test in folds:
        assert dates[train].max() < dates[test].min()
        assert dates[test].nunique() == 2


def test_incomplete_test_window_yields_no_fold() -> None:
    assert list(rolling_origin_splits([date(2025, 1, 6)], 1, 1, 1)) == []


def test_unsigned_numpy_horizon_larger_than_history_yields_no_fold() -> None:
    dates = [date(2025, 1, 6), date(2025, 1, 13)]
    assert list(rolling_origin_splits(dates, 1, np.uint64(4), 1)) == []


@pytest.mark.parametrize("sizes", [(0, 1, 1), (1, 0, 1), (1, 1, -1)])
def test_split_sizes_must_be_positive(sizes: tuple[int, int, int]) -> None:
    with pytest.raises(ValueError, match="positive"):
        list(rolling_origin_splits([date(2025, 1, 6)], *sizes))


def test_missing_split_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="dates"):
        list(rolling_origin_splits([pd.Timestamp("2025-01-06"), pd.NaT], 1, 1, 1))
