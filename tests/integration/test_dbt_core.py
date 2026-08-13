from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import duckdb
from dbt.cli.main import dbtRunner

from sales_analytics.generation.generator import GeneratorConfig, generate_dataset
from sales_analytics.ingestion.bronze import bootstrap_warehouse, ingest_to_bronze
from sales_analytics.ingestion.validate import validate_sources

PROJECT_ROOT = Path(__file__).parents[2]
DBT_PROJECT_DIR = PROJECT_ROOT / "analytics_dbt"


def test_dbt_core_builds_star_schema_and_reconciles_financials(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    config = replace(
        configured,
        customer_count=10,
        error_rates={name: 0.01 for name in configured.error_rates},
    )
    dataset = generate_dataset(config)
    dataset = replace(
        dataset,
        calendar_events=dataset.calendar_events.drop(index=500).reset_index(drop=True),
    )
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        ingest_to_bronze(
            dataset,
            validate_sources(dataset, load_id="dbt-core"),
            connection,
            load_id="dbt-core",
        )

    monkeypatch.setenv("SALES_DUCKDB_PATH", str(warehouse_path))
    common_args = [
        "--project-dir",
        str(DBT_PROJECT_DIR),
        "--profiles-dir",
        str(DBT_PROJECT_DIR),
        "--target-path",
        str(tmp_path / "target"),
        "--log-path",
        str(tmp_path / "logs"),
    ]
    silver_result = dbtRunner().invoke(
        ["build", "--select", "staging intermediate", *common_args]
    )
    core_result = dbtRunner().invoke(
        ["build", "--select", "marts.core+", *common_args]
    )

    assert silver_result.success, silver_result.exception
    assert core_result.success, core_result.exception
    manifest = json.loads((tmp_path / "target" / "manifest.json").read_text())
    not_null_columns = {
        "model.sales_analytics.fact_sales": set(),
        "model.sales_analytics.fact_returns": set(),
    }
    for node in manifest["nodes"].values():
        model = node.get("attached_node")
        metadata = node.get("test_metadata") or {}
        if model in not_null_columns and metadata.get("name") == "not_null":
            not_null_columns[model].add(node["column_name"])

    assert not_null_columns == {
        "model.sales_analytics.fact_sales": {
            "line_id",
            "date_key",
            "customer_id",
            "product_id",
            "channel_key",
            "geography_key",
            "payment_method_key",
        },
        "model.sales_analytics.fact_returns": {
            "return_id",
            "line_id",
            "return_date_key",
            "order_date_key",
            "customer_id",
            "product_id",
            "channel_key",
            "geography_key",
            "payment_method_key",
        },
    }
    with duckdb.connect(str(warehouse_path)) as connection:
        core_views = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'gold'
                  AND (table_name LIKE 'dim_%' OR table_name LIKE 'fact_%')
                """
            ).fetchall()
        }
        counts = {
            model: connection.execute(
                f"SELECT count(*) FROM gold.{model}"
            ).fetchone()[0]
            for model in core_views
        }
        date_coverage = connection.execute(
            """
            SELECT
                count(*),
                datediff('day', min(full_date), max(full_date)) + 1
            FROM gold.dim_date
            """
        ).fetchone()
        money_types = dict(
            connection.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'gold'
                  AND table_name = 'fact_sales'
                  AND column_name IN (
                      'gross_sales', 'discount_amount', 'net_sales',
                      'cogs', 'gross_profit'
                  )
                """
            ).fetchall()
        )
        financial_failures = connection.execute(
            """
            SELECT count(*)
            FROM gold.fact_sales
            WHERE gross_sales <> round(ordered_quantity * unit_price, 2)
               OR discount_amount <> round(gross_sales * discount_rate, 2)
               OR net_sales <> gross_sales - discount_amount
               OR cogs <> round(ordered_quantity * unit_cost, 2)
               OR gross_profit <> net_sales - cogs
            """
        ).fetchone()[0]
        return_failures = connection.execute(
            """
            SELECT count(*)
            FROM gold.fact_returns
            WHERE returned_revenue
                    <> round(returned_quantity * unit_price * (1 - discount_rate), 2)
               OR reversed_cogs <> round(returned_quantity * unit_cost, 2)
               OR profit_impact <> returned_revenue - reversed_cogs
            """
        ).fetchone()[0]

    assert core_views == {
        "dim_date",
        "dim_customer",
        "dim_product",
        "dim_channel",
        "dim_geography",
        "dim_promotion",
        "dim_payment_method",
        "fact_sales",
        "fact_returns",
    }
    assert counts["fact_sales"] == 77
    assert counts["fact_returns"] == 11
    assert counts["dim_customer"] == 9
    assert counts["dim_product"] == 11
    assert date_coverage == (1096, 1096)
    assert set(money_types.values()) == {"DECIMAL(18,2)"}
    assert financial_failures == 0
    assert return_failures == 0
