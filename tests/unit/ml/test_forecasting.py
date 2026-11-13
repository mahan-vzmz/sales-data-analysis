import pandas as pd
import pytest

from sales_analytics.ml.forecasting import (
    forecast_errors,
    last_value,
    seasonal_naive,
    select_champion,
)


def test_baselines_repeat_last_value_and_cycle_last_season() -> None:
    history = [9.0, 2.0, 4.0, 6.0]
    assert last_value(history, 5) == [6.0] * 5
    assert seasonal_naive(history, 5, season_length=3) == [2.0, 4.0, 6.0, 2.0, 4.0]
    with pytest.raises(ValueError, match="season"):
        seasonal_naive(history, 1, season_length=5)


def test_errors_match_hand_calculation_including_zero_pairs() -> None:
    result = forecast_errors([0, 0, 6], [0, 3, 2])
    assert result["mae"] == pytest.approx(7 / 3)
    assert result["smape"] == pytest.approx(100)


def test_selection_requires_strict_improvement_over_best_baseline() -> None:
    scores = pd.Series(
        {"last_value": 5.0, "seasonal_naive": 4.0, "ridge": 4.0, "random_forest": 6.0}
    )
    assert select_champion(scores) == "seasonal_naive"
    scores["ridge"] = 3.9
    assert select_champion(scores) == "ridge"

    holdout = pd.Series({"last_value": 1.0, "seasonal_naive": 7.0, "ridge": 8.0})
    assert select_champion(scores, holdout_mae=holdout) == "seasonal_naive"
    holdout["ridge"] = 6.9
    assert select_champion(scores, holdout_mae=holdout) == "ridge"
