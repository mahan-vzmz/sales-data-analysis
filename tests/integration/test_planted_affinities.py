from dataclasses import replace
from pathlib import Path

import duckdb
import pytest
from dbt.cli.main import dbtRunner

from sales_analytics.analytics.baskets import build_basket_rules
from sales_analytics.generation.generator import GeneratorConfig, generate_dataset
from sales_analytics.ingestion.bronze import bootstrap_warehouse, ingest_to_bronze
from sales_analytics.ingestion.validate import validate_sources

PROJECT_ROOT = Path(__file__).parents[2]
DBT_PROJECT_DIR = PROJECT_ROOT / "analytics_dbt"


def test_planted_laptop_mouse_affinity_survives_through_gold_mart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    config = replace(configured, error_rates=dict.fromkeys(configured.error_rates, 0.0))
    dataset = generate_dataset(config)
    warehouse = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse)
    with duckdb.connect(str(warehouse)) as connection:
        ingest_to_bronze(
            dataset,
            validate_sources(dataset, load_id="planted-affinities"),
            connection,
            load_id="planted-affinities",
        )

    monkeypatch.setenv("SALES_DUCKDB_PATH", str(warehouse))
    build = dbtRunner().invoke(
        [
            "build",
            "--select",
            "+mart_basket_base",
            "--indirect-selection=cautious",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROJECT_DIR),
            "--target-path",
            str(tmp_path / "target"),
            "--log-path",
            str(tmp_path / "logs"),
        ]
    )
    assert build.success, build.exception
    with duckdb.connect(str(warehouse)) as connection:
        baskets = connection.sql(
            "select order_id, product_id from gold.mart_basket_base"
        ).df()

    rules = build_basket_rules(baskets).set_index(["antecedent", "consequent"])
    planted = rules.loc[("PROD-001", "PROD-003"), :]
    controls = rules.loc[[("PROD-001", "PROD-004"), ("PROD-001", "PROD-005")], "lift"]
    assert planted["support"] >= 0.04
    assert planted["confidence"] >= 0.35
    assert planted["lift"] >= 1.3
    assert planted["lift"] > controls.max()
