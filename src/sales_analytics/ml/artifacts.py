"""Portable forecast results and model metadata."""

import json
from pathlib import Path

from .forecasting import BacktestResult
from .propensity import PropensityResult


def write_forecast_artifact(
    path: Path, result: BacktestResult, *, data_version: str
) -> None:
    """Save the selected model's held-out forecast and evaluation metadata."""
    last_fold = result.predictions["fold"].max()
    forecast = result.predictions.loc[
        result.predictions["fold"].eq(last_fold)
        & result.predictions["model"].eq(result.champion)
    ]
    features = {
        "last_value": ["ordered_quantity_lag_1"],
        "seasonal_naive": [f"ordered_quantity_lag_{result.season_length}"],
    }
    payload = {
        "model": result.champion,
        "validation_winner": result.validation_winner,
        "model_version": "1",
        "data_version": data_version,
        "target": "ordered_quantity",
        "training_cutoff": forecast["training_cutoff"].max().date().isoformat(),
        "horizon": int(forecast["horizon_week"].max()),
        "features": features.get(result.champion, list(result.features)),
        "selection_metric": "mae",
        "validation_metrics": result.validation_metrics.to_dict(orient="records"),
        "holdout_metrics": result.holdout_metrics.to_dict(orient="records"),
        "fold_metrics": result.fold_metrics.to_dict(orient="records"),
        "horizon_metrics": result.horizon_metrics.to_dict(orient="records"),
        "predictions": json.loads(
            forecast[["category", "week_start", "horizon_week", "prediction"]].to_json(
                orient="records", date_format="iso"
            )
        ),
    }
    content = json.dumps(payload, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")


def write_propensity_artifact(
    path: Path, result: PropensityResult, *, data_version: str
) -> None:
    """Save held-out inactivity probabilities and evaluation metadata."""
    tables = {
        "validation_metrics": result.validation_metrics,
        "test_metrics": result.test_metrics,
        "calibration": result.calibration,
        "segment_errors": result.segment_errors,
        "predictions": result.predictions[["customer_id", "cutoff", "probability"]],
    }
    payload = {
        "model": result.champion,
        "validation_winner": result.validation_winner,
        "model_version": "1",
        "data_version": data_version,
        "target": "inactive_label",
        "training_cutoff": result.training_cutoff,
        "horizon_days": result.horizon_days,
        "features": list(result.features),
        "selection_metric": "brier",
        **{
            name: json.loads(frame.to_json(orient="records", date_format="iso"))
            for name, frame in tables.items()
        },
    }
    content = json.dumps(payload, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")
