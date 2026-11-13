import json
from dataclasses import replace
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from dbt.cli.main import dbtRunner
from pandas.testing import assert_series_equal

from sales_analytics.generation.generator import GeneratorConfig, generate_dataset
from sales_analytics.ingestion.bronze import bootstrap_warehouse, ingest_to_bronze
from sales_analytics.ingestion.validate import validate_sources
from sales_analytics.ml.artifacts import write_forecast_artifact
from sales_analytics.ml.forecasting import run_backtest

ROOT = Path(__file__).parents[2]


def test_gold_backtest_keeps_the_final_window_unseen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = GeneratorConfig.from_json(ROOT / "data/fixtures/generator_config.json")
    config = replace(config, error_rates=dict.fromkeys(config.error_rates, 0.0))
    dataset = generate_dataset(config)
    warehouse = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse)
    with duckdb.connect(str(warehouse)) as con:
        ingest_to_bronze(
            dataset,
            validate_sources(dataset, load_id="forecast-test"),
            con,
            load_id="forecast-test",
        )
    monkeypatch.setenv("SALES_DUCKDB_PATH", str(warehouse))
    project = str(ROOT / "analytics_dbt")
    built = dbtRunner().invoke(
        [
            "run",
            "--select",
            "+mart_forecasting_base",
            "--project-dir",
            project,
            "--profiles-dir",
            project,
            "--target-path",
            str(tmp_path / "target"),
            "--log-path",
            str(tmp_path / "logs"),
        ]
    )
    assert built.success, built.exception
    with duckdb.connect(str(warehouse)) as con:
        weekly = con.sql("select * from gold.mart_forecasting_base").df()

    coverage = {"coverage_start": config.start_date, "coverage_end": config.end_date}
    result = run_backtest(weekly, min_train=140, horizon=4, **coverage)
    predictions = result.predictions
    assert (predictions["training_cutoff"] < predictions["week_start"]).all()
    assert set(predictions["model"]) == {
        "last_value",
        "seasonal_naive",
        "ridge",
        "random_forest",
    }
    assert predictions.groupby("fold")["week_start"].nunique().eq(4).all()
    assert predictions.groupby(["fold", "model"]).size().eq(24).all()
    assert set(result.horizon_metrics["horizon_week"]) == {1, 2, 3, 4}
    assert result.fold_metrics["mae"].notna().all()
    final_fold = predictions["fold"].max()
    holdout = predictions[predictions["fold"] == final_fold]
    assert holdout["week_start"].max() == pd.Timestamp("2025-12-22")
    assert predictions["training_cutoff"].min() >= pd.Timestamp("2023-01-02")

    changed = weekly.copy()
    changed.loc[
        changed["week_start"] >= holdout["week_start"].min(),
        ["ordered_quantity", "average_unit_price", "promoted_order_count"],
    ] = 10_000
    rerun = run_backtest(changed, min_train=140, horizon=4, **coverage)
    assert rerun.validation_winner == result.validation_winner
    assert_series_equal(predictions["prediction"], rerun.predictions["prediction"])
    assert not holdout["actual"].equals(
        rerun.predictions.loc[rerun.predictions["fold"] == final_fold, "actual"]
    )

    path = tmp_path / "forecast.json"
    write_forecast_artifact(path, result, data_version="forecast-test")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["model"] == result.champion
    assert artifact["data_version"] == "forecast-test"
    assert artifact["training_cutoff"] == "2025-11-24"
    assert artifact["horizon"] == 4
    assert len(artifact["predictions"]) == 24
    assert len(artifact["fold_metrics"]) == 4 * predictions["fold"].nunique()
    assert len(artifact["horizon_metrics"]) == 2 * 4 * 4 * 6
