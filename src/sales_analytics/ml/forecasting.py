"""Fixed-origin backtests of weekly category demand."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from itertools import cycle, islice
from numbers import Integral

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor  # type: ignore[import-untyped]
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]

from .features import build_forecast_features, rolling_origin_splits

_BASELINES = ("last_value", "seasonal_naive")
_CANDIDATES = ("ridge", "random_forest")
_TARGET = "ordered_quantity"
_CALENDAR = ["iso_week", "holiday_days", "campaign_days"]
_WARMUP = "ordered_quantity_rolling_mean_4"


@dataclass(frozen=True)
class BacktestResult:
    predictions: pd.DataFrame
    fold_metrics: pd.DataFrame
    horizon_metrics: pd.DataFrame
    validation_metrics: pd.DataFrame
    holdout_metrics: pd.DataFrame
    validation_winner: str
    champion: str
    features: tuple[str, ...]
    season_length: int


def last_value(history: Sequence[float], horizon: int) -> list[float]:
    """Repeat the last observation for the entire forecast horizon."""
    if not len(history) or horizon < 1:
        raise ValueError("last-value forecast requires history and a positive horizon")
    return [history[-1]] * horizon


def seasonal_naive(
    history: Sequence[float], horizon: int, season_length: int = 52
) -> list[float]:
    """Repeat the last complete season without reading future observations."""
    if season_length < 1 or len(history) < season_length:
        raise ValueError("seasonal-naive forecast requires a complete season")
    if horizon < 1:
        raise ValueError("horizon must be positive")
    return list(islice(cycle(history[-season_length:]), horizon))


def forecast_errors(
    actual: Sequence[float], prediction: Sequence[float]
) -> dict[str, float]:
    """Compute MAE in units and sMAPE on a 0–200 percent scale."""
    observed, estimated = (
        np.asarray(actual, dtype=float),
        np.asarray(prediction, dtype=float),
    )
    if observed.ndim != 1 or observed.shape != estimated.shape or not observed.size:
        raise ValueError(
            "actual and prediction must be nonempty vectors of equal length"
        )
    if not np.isfinite(observed).all() or not np.isfinite(estimated).all():
        raise ValueError("actual and prediction must be finite")
    error = np.abs(observed - estimated)
    scale = np.abs(observed) + np.abs(estimated)
    relative = np.divide(error, scale, out=np.zeros_like(error), where=scale != 0)
    return {"mae": float(error.mean()), "smape": float(200 * relative.mean())}


def select_champion(
    validation_mae: pd.Series, *, holdout_mae: pd.Series | None = None
) -> str:
    """Nominate by validation MAE and optionally gate the nominee on holdout."""
    baseline = str(validation_mae.loc[list(_BASELINES)].idxmin())
    candidate = str(validation_mae.loc[list(_CANDIDATES)].idxmin())
    if validation_mae[candidate] >= validation_mae[baseline]:
        return baseline
    if holdout_mae is not None and holdout_mae[candidate] >= holdout_mae[baseline]:
        return baseline
    return candidate


def _metrics(predictions: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = [
        {
            **dict(zip(keys, group_key, strict=True)),
            **forecast_errors(group["actual"].tolist(), group["prediction"].tolist()),
        }
        for group_key, group in predictions.groupby(keys)
    ]
    return pd.DataFrame(rows)


def run_backtest(
    weekly_sales: pd.DataFrame,
    *,
    coverage_start: date,
    coverage_end: date,
    min_train: int = 104,
    horizon: int = 4,
    season_length: int = 52,
) -> BacktestResult:
    """Compare four methods on complete weeks, reserving the final fold for reporting.

    Each direct candidate gets history from one origin and calendar values for
    the target week. All validation windows and the final holdout are disjoint.
    """
    if any(
        not isinstance(size, Integral) or isinstance(size, bool) or size < 1
        for size in (min_train, horizon, season_length)
    ):
        raise ValueError(
            "min_train, horizon and season_length must be positive integers"
        )
    min_train, horizon, season_length = int(min_train), int(horizon), int(season_length)
    if min_train < max(season_length, horizon + 4):
        raise ValueError(
            "min_train must cover a season and the feature warmup plus horizon"
        )

    start, end = pd.Timestamp(coverage_start), pd.Timestamp(coverage_end)
    if pd.isna(start) or pd.isna(end) or start > end:
        raise ValueError("coverage must have a valid start and end")
    week = pd.to_datetime(weekly_sales["week_start"]).dt.normalize()
    if week.isna().any():
        raise ValueError("week_start must be present")
    complete = weekly_sales.loc[week.ge(start) & (week + pd.Timedelta(days=6)).le(end)]
    features = build_forecast_features(complete)
    weeks = pd.date_range(start, end - pd.Timedelta(days=6), freq="W-MON")
    category_counts = features.groupby("week_start")["category"].nunique()
    if (
        not category_counts.index.equals(weeks)
        or not category_counts.eq(features["category"].nunique()).all()
    ):
        raise ValueError("coverage requires a complete week/category panel")
    if len(weeks) < min_train + 2 * horizon:
        raise ValueError("coverage requires a validation window and a final holdout")
    target = features[_TARGET].to_numpy(dtype=float)
    if not np.isfinite(target).all() or (target < 0).any():
        raise ValueError("ordered_quantity must be finite and nonnegative")
    lagged = [
        column
        for column in features
        if isinstance(column, str) and column.endswith("_lag_1")
    ] + [_WARMUP]
    model_features = [*lagged, *_CALENDAR]
    initial_train = min_train + (len(weeks) - min_train) % horizon
    folds = rolling_origin_splits(
        features["week_start"], initial_train, horizon, horizon
    )

    output = []
    for fold, (train_idx, test_idx) in enumerate(folds, start=1):
        train = features.iloc[train_idx]
        test = features.iloc[test_idx]
        training_cutoff = train["week_start"].max()
        first_week = test["week_start"].min()
        origin = test.loc[test["week_start"].eq(first_week)].set_index("category")
        by_category = train.groupby("category")
        for name in _BASELINES:
            values = []
            for _, history in by_category:
                series = history[_TARGET].tolist()
                values.extend(
                    last_value(series, horizon)
                    if name == "last_value"
                    else seasonal_naive(series, horizon, season_length)
                )
            output.append(
                test[["category", "week_start", _TARGET]].assign(
                    model=name,
                    prediction=values,
                    fold=fold,
                    training_cutoff=training_cutoff,
                )
            )

        for offset, (test_week, target_week) in enumerate(test.groupby("week_start")):
            labels = by_category[_TARGET].shift(-offset)
            known_calendar = by_category[_CALENDAR].shift(-offset)
            ready = labels.notna() & train[_WARMUP].notna()
            train_x = train.loc[ready, lagged].join(known_calendar.loc[ready]).fillna(0)
            test_x = target_week[["category", *_CALENDAR]].join(
                origin[lagged], on="category"
            )
            estimators = (
                Ridge(alpha=10),
                RandomForestRegressor(
                    n_estimators=40, max_depth=6, min_samples_leaf=4, random_state=42
                ),
            )
            for name, estimator in zip(_CANDIDATES, estimators, strict=True):
                estimator.fit(train_x[model_features], labels.loc[ready])
                values = estimator.predict(test_x[model_features].fillna(0)).clip(min=0)
                output.append(
                    target_week[["category", "week_start", _TARGET]].assign(
                        model=name,
                        prediction=values,
                        fold=fold,
                        training_cutoff=training_cutoff,
                    )
                )

    predictions = pd.concat(output, ignore_index=True).rename(
        columns={_TARGET: "actual"}
    )
    predictions["horizon_week"] = (
        predictions["week_start"] - predictions["training_cutoff"]
    ).dt.days // 7
    predictions = predictions.sort_values(
        ["fold", "model", "week_start", "category"], ignore_index=True
    )
    holdout = predictions["fold"].eq(predictions["fold"].max())
    validation_metrics = _metrics(predictions.loc[~holdout], ["model"])
    holdout_metrics = _metrics(predictions.loc[holdout], ["model"])
    validation_mae = validation_metrics.set_index("model")["mae"]
    return BacktestResult(
        predictions=predictions,
        fold_metrics=_metrics(predictions, ["fold", "model"]),
        horizon_metrics=_metrics(
            predictions.assign(split=np.where(holdout, "holdout", "validation")),
            ["split", "model", "horizon_week", "category"],
        ),
        validation_metrics=validation_metrics,
        holdout_metrics=holdout_metrics,
        validation_winner=select_champion(validation_mae),
        champion=select_champion(
            validation_mae, holdout_mae=holdout_metrics.set_index("model")["mae"]
        ),
        features=tuple(model_features),
        season_length=season_length,
    )
