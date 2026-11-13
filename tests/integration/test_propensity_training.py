import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from sales_analytics.analytics.churn import build_customer_snapshots
from sales_analytics.generation.generator import GeneratorConfig, generate_dataset
from sales_analytics.ml.artifacts import write_propensity_artifact
from sales_analytics.ml.propensity import run_propensity

ROOT = Path(__file__).parents[2]


def test_propensity_trains_on_historical_customer_snapshots(tmp_path: Path) -> None:
    base = GeneratorConfig.from_json(ROOT / "data/fixtures/generator_config.json")
    config = replace(
        base,
        patterns=replace(base.patterns, return_probability=0),
        error_rates=dict.fromkeys(base.error_rates, 0.0),
    )
    dataset = generate_dataset(config)
    orders = dataset.orders
    events = (
        orders[["customer_id", "order_timestamp"]]
        .rename(columns={"order_timestamp": "event_date"})
        .assign(event_type="completed_purchase")
    )
    snapshots = build_customer_snapshots(
        events,
        pd.date_range("2023-03-31", "2025-06-30", freq="ME").date,
        120,
        observation_end=config.end_date,
    ).assign(
        segment=lambda rows: rows["customer_id"].map(
            dataset.customers.set_index("customer_id")["segment"]
        )
    )
    boundaries = {"validation_start": date(2024, 6, 1), "test_start": date(2025, 1, 1)}
    result = run_propensity(snapshots, **boundaries)
    assert result.validation_winner == "random_forest"
    assert result.champion == "recency"
    assert result.test_metrics.set_index("model")["brier"].idxmin() == "majority"
    assert set(result.validation_metrics["model"]) == {
        "majority",
        "recency",
        "logistic",
        "random_forest",
    }
    assert result.predictions["probability"].between(0, 1).all()
    assert result.predictions["cutoff"].min() >= pd.Timestamp("2025-01-01")
    assert result.calibration["count"].sum() == len(result.predictions)
    assert result.segment_errors["count"].sum() == len(result.predictions)
    assert result.test_metrics["roc_auc"].between(0, 1).all()
    assert result.test_metrics["pr_auc"].between(0, 1).all()
    assert result.test_metrics["brier"].between(0, 1).all()

    changed = snapshots.copy()
    test_rows = changed["cutoff"].ge(pd.Timestamp("2025-01-01"))
    changed.loc[test_rows, "inactive_label"] = (
        1 - changed.loc[test_rows, "inactive_label"]
    )
    rerun = run_propensity(changed, **boundaries)
    assert result.validation_winner == rerun.validation_winner
    assert_frame_equal(result.validation_metrics, rerun.validation_metrics)
    assert_frame_equal(result.test_probabilities, rerun.test_probabilities)

    path = tmp_path / "propensity.json"
    write_propensity_artifact(path, result, data_version="synthetic-seed-42-no-returns")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["model"] == result.champion
    assert artifact["horizon_days"] == 120
    assert len(artifact["predictions"]) == len(result.predictions)
