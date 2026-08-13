from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb
from dbt.cli.main import dbtRunner

from sales_analytics.generation.generator import GeneratorConfig, generate_dataset
from sales_analytics.ingestion.bronze import bootstrap_warehouse, ingest_to_bronze
from sales_analytics.ingestion.contracts import SOURCE_TABLES
from sales_analytics.ingestion.validate import validate_sources

PROJECT_ROOT = Path(__file__).parents[2]
DBT_PROJECT_DIR = PROJECT_ROOT / "analytics_dbt"


def test_dbt_staging_preserves_bronze_grain_and_standardizes_types(
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
    validation = validate_sources(dataset, load_id="dbt-staging")
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        ingest_to_bronze(
            dataset,
            validation,
            connection,
            load_id="dbt-staging",
        )

    profile_example = DBT_PROJECT_DIR / "profiles.yml.example"
    assert profile_example.exists(), "dbt profile example is missing"
    assert DBT_PROJECT_DIR.joinpath("profiles.yml").exists(), "dbt profile is missing"
    monkeypatch.setenv("SALES_DUCKDB_PATH", str(warehouse_path))

    result = dbtRunner().invoke(
        [
            "build",
            "--select",
            "staging",
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

    assert result.success, result.exception
    with duckdb.connect(str(warehouse_path)) as connection:
        staging_views = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'silver'
                """
            ).fetchall()
        }
        staging_counts = {
            table: connection.execute(
                f"SELECT count(*) FROM silver.stg_{table}"
            ).fetchone()[0]
            for table in SOURCE_TABLES
        }
        staging_schemas = dict(
            connection.execute(
                """
                SELECT
                    table_name,
                    string_agg(
                        column_name || ':' || data_type,
                        ',' ORDER BY ordinal_position
                    )
                FROM information_schema.columns
                WHERE table_schema = 'silver'
                  AND table_name LIKE 'stg_%'
                GROUP BY table_name
                """
            ).fetchall()
        )

    assert staging_views == {f"stg_{table}" for table in SOURCE_TABLES}
    assert staging_counts == {
        table: len(getattr(dataset, table)) for table in SOURCE_TABLES
    }
    assert staging_schemas == {
        "stg_customers": "customer_id:VARCHAR,signup_date:DATE,home_city:VARCHAR,"
        "segment:VARCHAR,_load_id:VARCHAR,_source_file:VARCHAR,_source_row:BIGINT,"
        "_ingested_at:TIMESTAMP",
        "stg_products": "product_id:VARCHAR,product_name:VARCHAR,category:VARCHAR,"
        "base_price:DECIMAL(18,2),base_cost:DECIMAL(18,2),_load_id:VARCHAR,"
        "_source_file:VARCHAR,_source_row:BIGINT,_ingested_at:TIMESTAMP",
        "stg_orders": "order_id:VARCHAR,customer_id:VARCHAR,order_timestamp:TIMESTAMP,"
        "channel:VARCHAR,payment_method:VARCHAR,promotion_id:VARCHAR,_load_id:VARCHAR,"
        "_source_file:VARCHAR,_source_row:BIGINT,_ingested_at:TIMESTAMP",
        "stg_order_items": "line_id:VARCHAR,order_id:VARCHAR,product_id:VARCHAR,"
        "quantity:BIGINT,unit_price:DECIMAL(18,2),unit_cost:DECIMAL(18,2),"
        "discount_rate:DECIMAL(9,4),_load_id:VARCHAR,_source_file:VARCHAR,"
        "_source_row:BIGINT,_ingested_at:TIMESTAMP",
        "stg_returns": "return_id:VARCHAR,line_id:VARCHAR,return_date:DATE,"
        "returned_quantity:BIGINT,reason:VARCHAR,_load_id:VARCHAR,"
        "_source_file:VARCHAR,_source_row:BIGINT,_ingested_at:TIMESTAMP",
        "stg_promotions": "promotion_id:VARCHAR,promotion_type:VARCHAR,start_date:DATE,"
        "end_date:DATE,discount_policy:DECIMAL(9,4),_load_id:VARCHAR,"
        "_source_file:VARCHAR,_source_row:BIGINT,_ingested_at:TIMESTAMP",
        "stg_calendar_events": "event_date:DATE,holiday:VARCHAR,campaign:VARCHAR,"
        "seasonal_event:VARCHAR,_load_id:VARCHAR,_source_file:VARCHAR,"
        "_source_row:BIGINT,_ingested_at:TIMESTAMP",
    }


def test_dbt_profile_default_path_is_relative_to_invocation_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("SALES_DUCKDB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    bootstrap_warehouse(tmp_path / "warehouse" / "sales.duckdb")

    result = dbtRunner().invoke(
        [
            "debug",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROJECT_DIR),
        ]
    )

    assert result.success, result.exception
