import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from sales_analytics.ml.features import build_forecast_features


@pytest.fixture
def weekly_sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "week_start": list(pd.date_range("2025-01-06", periods=6, freq="W-MON"))
            * 2,
            "category": ["A"] * 6 + ["B"] * 6,
            "ordered_quantity": [2, 4, 6, 8, 100, 200, 30, 40, 50, 60, 70, 80],
            "holiday_days": [0] * 12,
            "campaign_days": [1] * 12,
            "promoted_order_count": [1, 2, 3, 4, 5, 6] * 2,
            "average_unit_price": [10, 20, 30, 40, 50, 60] * 2,
            "effective_discount_rate": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5] * 2,
            "online_unit_share": [0.5] * 12,
            "store_unit_share": [0.3] * 12,
            "marketplace_unit_share": [0.2] * 12,
            "return_adjusted_revenue": [999] * 12,
        }
    )


def test_lags_and_rolling_use_prior_weeks_in_each_category(
    weekly_sales: pd.DataFrame,
) -> None:
    before = weekly_sales.copy()
    result = build_forecast_features(weekly_sales.iloc[::-1]).set_index(
        ["category", "week_start"]
    )
    first = pd.Timestamp("2025-01-06")
    fifth = pd.Timestamp("2025-02-03")

    assert pd.isna(result.loc[("B", first), "ordered_quantity_lag_1"])
    assert pd.isna(
        result.loc[("A", pd.Timestamp("2025-01-27")), "ordered_quantity_rolling_mean_4"]
    )
    assert result.loc[("A", fifth), "ordered_quantity_lag_1"] == 8
    assert result.loc[("A", fifth), "ordered_quantity_rolling_mean_4"] == 5
    assert result.loc[("B", fifth), "ordered_quantity_rolling_mean_4"] == 45
    assert result.loc[("A", fifth), "average_unit_price_lag_1"] == 40
    assert result.loc[("A", fifth), "effective_discount_rate_lag_1"] == 0.3
    assert result.loc[("A", fifth), "promoted_order_count_lag_1"] == 4
    assert result.loc[("A", fifth), "online_unit_share_lag_1"] == 0.5
    assert result.loc[("A", fifth), "store_unit_share_lag_1"] == 0.3
    assert result.loc[("A", fifth), "marketplace_unit_share_lag_1"] == 0.2
    assert result.loc[("A", fifth), "iso_week"] == 6
    assert result.loc[("A", fifth), "campaign_days"] == 1
    assert "return_adjusted_revenue" not in result
    assert_frame_equal(weekly_sales, before)


def test_changing_current_and_future_sales_cannot_change_current_features(
    weekly_sales: pd.DataFrame,
) -> None:
    cutoff = pd.Timestamp("2025-02-03")
    modified = weekly_sales.copy()
    modified.loc[
        modified["week_start"] >= cutoff, ["ordered_quantity", "average_unit_price"]
    ] = 9999

    before = build_forecast_features(weekly_sales)
    after = build_forecast_features(modified)
    assert_frame_equal(
        before.loc[before["week_start"] <= cutoff].drop(columns="ordered_quantity"),
        after.loc[after["week_start"] <= cutoff].drop(columns="ordered_quantity"),
    )


def test_gaps_and_duplicate_category_weeks_are_rejected(
    weekly_sales: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="consecutive"):
        build_forecast_features(weekly_sales.drop(index=2))
    with pytest.raises(ValueError, match="unique"):
        build_forecast_features(pd.concat([weekly_sales, weekly_sales.iloc[:1]]))


def test_week_keys_are_calendar_dates(weekly_sales: pd.DataFrame) -> None:
    shifted = weekly_sales.copy()
    shifted.loc[shifted["category"] == "B", "week_start"] += pd.Timedelta(hours=18)

    assert_frame_equal(
        build_forecast_features(shifted), build_forecast_features(weekly_sales)
    )
