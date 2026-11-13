"""Chronological evaluation of customer inactivity probabilities."""

from dataclasses import dataclass
from datetime import date

import pandas as pd
from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)

_FEATURES = ("recency_days", "completed_order_count", "return_count")
_LABEL = "inactive_label"
_BASELINES = ("majority", "recency")
_CANDIDATES = ("logistic", "random_forest")


@dataclass(frozen=True)
class PropensityResult:
    validation_metrics: pd.DataFrame
    test_metrics: pd.DataFrame
    test_probabilities: pd.DataFrame
    predictions: pd.DataFrame
    calibration: pd.DataFrame
    segment_errors: pd.DataFrame
    validation_winner: str
    champion: str
    training_cutoff: str
    horizon_days: int
    features: tuple[str, ...]


def split_snapshots(
    snapshots: pd.DataFrame, validation_start: date, test_start: date
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Keep each cutoff together and purge labels overlapping the next period."""
    validation_boundary, test_boundary = (
        pd.Timestamp(validation_start),
        pd.Timestamp(test_start),
    )
    if not validation_boundary < test_boundary:
        raise ValueError("validation_start must precede test_start")
    cutoff = pd.to_datetime(snapshots["cutoff"])
    horizon = pd.to_datetime(snapshots["horizon_end"])
    feature_date = pd.to_datetime(snapshots["last_feature_event_date"])
    if cutoff.isna().any() or horizon.isna().any() or horizon.le(cutoff).any():
        raise ValueError("Each snapshot needs a valid cutoff and later horizon_end")
    if feature_date.isna().any() or feature_date.gt(cutoff).any():
        raise ValueError("Every feature timestamp must be on or before its cutoff")
    return (
        snapshots.loc[cutoff.lt(validation_boundary) & horizon.lt(validation_boundary)],
        snapshots.loc[
            cutoff.ge(validation_boundary)
            & cutoff.lt(test_boundary)
            & horizon.lt(test_boundary)
        ],
        snapshots.loc[cutoff.ge(test_boundary)],
    )


def majority_probability(train: pd.DataFrame) -> float:
    """Use training prevalence as a constant probability."""
    return float(train[_LABEL].mean())


def recency_probability(train: pd.DataFrame, recency_days: pd.Series) -> pd.Series:
    """Use training rates by 90-day recency band, with prevalence as fallback."""
    rates = train.groupby(train["recency_days"] // 90)[_LABEL].mean()
    return (recency_days // 90).map(rates).fillna(majority_probability(train))


def calibration_table(actual: pd.Series, probability: pd.Series) -> pd.DataFrame:
    """Compare predicted and observed rates in nonempty probability deciles."""
    rows = pd.DataFrame(
        {"actual": actual.to_numpy(), "probability": probability.to_numpy()}
    )
    rows["bin"] = (rows["probability"] * 10).astype(int).clip(upper=9)
    return rows.groupby("bin", as_index=False).agg(
        count=("actual", "size"),
        mean_probability=("probability", "mean"),
        observed_rate=("actual", "mean"),
    )


def _scores(actual: pd.Series, probability: pd.DataFrame) -> pd.DataFrame:
    two_classes = actual.nunique() == 2
    return pd.DataFrame(
        [
            {
                "model": name,
                "roc_auc": float(roc_auc_score(actual, values))
                if two_classes
                else None,
                "pr_auc": float(average_precision_score(actual, values))
                if two_classes
                else None,
                "brier": float(brier_score_loss(actual, values)),
            }
            for name, values in probability.items()
        ]
    )


def run_propensity(
    snapshots: pd.DataFrame, *, validation_start: date, test_start: date
) -> PropensityResult:
    """Fit fixed candidates on training rows and compare the nominee once on test."""
    rows = snapshots.reset_index(drop=True)
    if (
        rows["customer_id"].isna().any()
        or rows.duplicated(["customer_id", "cutoff"]).any()
    ):
        raise ValueError("Snapshot keys must be present and unique")
    if not rows[_LABEL].isin([0, 1]).all():
        raise ValueError("inactive_label must be binary")
    if (
        rows[list(_FEATURES)].isna().any().any()
        or rows[list(_FEATURES)].lt(0).any().any()
    ):
        raise ValueError("Snapshot features must be present and nonnegative")
    train, validation, test = split_snapshots(rows, validation_start, test_start)
    if train[_LABEL].nunique() != 2 or validation.empty or test.empty:
        raise ValueError("Need two training classes and nonempty validation and test")
    horizons = (
        pd.to_datetime(rows["horizon_end"]) - pd.to_datetime(rows["cutoff"])
    ).dt.days
    if horizons.nunique() != 1 or horizons.min() < 1:
        raise ValueError("All snapshots must share one positive label horizon")

    feature_columns = list(_FEATURES)
    logistic = LogisticRegression(max_iter=1000).fit(
        train[feature_columns], train[_LABEL]
    )
    forest = RandomForestClassifier(
        n_estimators=50, max_depth=5, min_samples_leaf=10, random_state=42
    ).fit(train[feature_columns], train[_LABEL])

    def probabilities(frame: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "majority": majority_probability(train),
                "recency": recency_probability(train, frame["recency_days"]),
                "logistic": logistic.predict_proba(frame[feature_columns])[:, 1],
                "random_forest": forest.predict_proba(frame[feature_columns])[:, 1],
            },
            index=frame.index,
        )

    validation_metrics = _scores(validation[_LABEL], probabilities(validation))
    validation_brier = validation_metrics.set_index("model")["brier"]
    baseline = str(validation_brier.loc[list(_BASELINES)].idxmin())
    candidate = str(validation_brier.loc[list(_CANDIDATES)].idxmin())
    nominee = (
        candidate
        if validation_brier[candidate] < validation_brier[baseline]
        else baseline
    )
    test_probabilities = probabilities(test)
    test_metrics = _scores(test[_LABEL], test_probabilities)
    test_brier = test_metrics.set_index("model")["brier"]
    champion = nominee if test_brier[nominee] < test_brier[baseline] else baseline
    selected = test_probabilities[champion]
    predictions = test[["customer_id", "cutoff", _LABEL]].assign(probability=selected)
    segments = (
        test["segment"].fillna("Unknown")
        if "segment" in test
        else pd.Series("All", index=test.index)
    )
    segment_errors = (
        predictions.assign(
            segment=segments, squared_error=(selected - test[_LABEL]) ** 2
        )
        .groupby("segment", as_index=False)
        .agg(
            count=(_LABEL, "size"),
            observed_rate=(_LABEL, "mean"),
            mean_probability=("probability", "mean"),
            brier=("squared_error", "mean"),
        )
    )
    selected_features = {
        "majority": (),
        "recency": ("recency_days",),
    }.get(champion, _FEATURES)
    return PropensityResult(
        validation_metrics=validation_metrics,
        test_metrics=test_metrics,
        test_probabilities=test_probabilities,
        predictions=predictions,
        calibration=calibration_table(test[_LABEL], selected),
        segment_errors=segment_errors,
        validation_winner=nominee,
        champion=champion,
        training_cutoff=pd.to_datetime(train["cutoff"]).max().date().isoformat(),
        horizon_days=int(horizons.iloc[0]),
        features=selected_features,
    )
