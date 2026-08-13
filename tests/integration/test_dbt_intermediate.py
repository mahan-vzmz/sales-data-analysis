from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb
from dbt.cli.main import dbtRunner

from sales_analytics.generation.generator import GeneratorConfig, generate_dataset
from sales_analytics.ingestion.bronze import bootstrap_warehouse, ingest_to_bronze
from sales_analytics.ingestion.validate import validate_sources

PROJECT_ROOT = Path(__file__).parents[2]
DBT_PROJECT_DIR = PROJECT_ROOT / "analytics_dbt"


def test_dbt_intermediate_excludes_traced_rejections_and_invalid_children(
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
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        ingest_to_bronze(
            dataset,
            validate_sources(dataset, load_id="dbt-intermediate"),
            connection,
            load_id="dbt-intermediate",
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
    staging_result = dbtRunner().invoke(
        ["build", "--select", "staging", *common_args]
    )
    intermediate_result = dbtRunner().invoke(
        ["build", "--select", "intermediate", *common_args]
    )

    assert staging_result.success, staging_result.exception
    assert intermediate_result.success, intermediate_result.exception
    with duckdb.connect(str(warehouse_path)) as connection:
        intermediate_views = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'silver'
                  AND table_name LIKE 'int_%'
                """
            ).fetchall()
        }

        assert intermediate_views == {
            "int_customers",
            "int_products",
            "int_promotions",
            "int_orders",
            "int_order_items",
            "int_returns",
            "int_promotion_assignments",
            "int_rejected_records",
        }

        accepted_models = intermediate_views - {"int_rejected_records"}
        counts = {
            model: connection.execute(
                f"SELECT count(*) FROM silver.{model}"
            ).fetchone()[0]
            for model in accepted_models
        }
        direct_rejections_remaining = connection.execute(
            """
            SELECT count(*)
            FROM (
                SELECT 'customers' AS source_table, _load_id, _source_row
                FROM silver.int_customers
                UNION ALL
                SELECT 'products', _load_id, _source_row FROM silver.int_products
                UNION ALL
                SELECT 'promotions', _load_id, _source_row FROM silver.int_promotions
                UNION ALL
                SELECT 'orders', _load_id, _source_row FROM silver.int_orders
                UNION ALL
                SELECT 'order_items', _load_id, _source_row
                FROM silver.int_order_items
                UNION ALL
                SELECT 'returns', _load_id, _source_row FROM silver.int_returns
            ) accepted
            JOIN audit.validation_failures failures
              ON failures.load_id = accepted._load_id
             AND failures.source_table = accepted.source_table
             AND (
                  failures.source_row IS NULL
                  OR failures.source_row = accepted._source_row
             )
            """
        ).fetchone()[0]
        business_rule_failures = connection.execute(
            """
            SELECT count(*)
            FROM silver.int_order_items items
            LEFT JOIN silver.int_orders orders USING (order_id)
            LEFT JOIN silver.int_customers customers USING (customer_id)
            LEFT JOIN silver.int_products products USING (product_id)
            WHERE items.quantity <= 0
               OR items.unit_cost < 0
               OR items.unit_price <= 0
               OR orders.order_id IS NULL
               OR customers.customer_id IS NULL
               OR products.product_id IS NULL
            """
        ).fetchone()[0]
        return_rule_failures = connection.execute(
            """
            SELECT count(*)
            FROM silver.int_returns returns
            LEFT JOIN silver.int_order_items items USING (line_id)
            LEFT JOIN silver.int_orders orders USING (order_id)
            WHERE items.line_id IS NULL
               OR returns.returned_quantity > items.quantity
               OR returns.return_date < cast(orders.order_timestamp AS date)
            """
        ).fetchone()[0]
        reconciliation_failures = connection.execute(
            """
            WITH source_counts(source_table, source_count) AS (
                SELECT 'customers', count(*) FROM silver.stg_customers
                UNION ALL SELECT 'products', count(*) FROM silver.stg_products
                UNION ALL SELECT 'promotions', count(*) FROM silver.stg_promotions
                UNION ALL SELECT 'orders', count(*) FROM silver.stg_orders
                UNION ALL SELECT 'order_items', count(*) FROM silver.stg_order_items
                UNION ALL SELECT 'returns', count(*) FROM silver.stg_returns
            ),
            accepted_counts(source_table, accepted_count) AS (
                SELECT 'customers', count(*) FROM silver.int_customers
                UNION ALL SELECT 'products', count(*) FROM silver.int_products
                UNION ALL SELECT 'promotions', count(*) FROM silver.int_promotions
                UNION ALL SELECT 'orders', count(*) FROM silver.int_orders
                UNION ALL SELECT 'order_items', count(*) FROM silver.int_order_items
                UNION ALL SELECT 'returns', count(*) FROM silver.int_returns
            ),
            rejected_counts AS (
                SELECT source_table, count(DISTINCT source_row) AS rejected_count
                FROM silver.int_rejected_records
                GROUP BY source_table
            )
            SELECT count(*)
            FROM source_counts sources
            JOIN accepted_counts accepted USING (source_table)
            LEFT JOIN rejected_counts rejected USING (source_table)
            WHERE sources.source_count
                <> accepted.accepted_count + coalesce(rejected.rejected_count, 0)
            """
        ).fetchone()[0]
        rejected_lineage = connection.execute(
            """
            SELECT count(*), count(source_file), count(rule_code), count(reason)
            FROM silver.int_rejected_records
            """
        ).fetchone()

    assert counts == {
        "int_customers": 9,
        "int_products": 11,
        "int_promotions": 3,
        "int_orders": 42,
        "int_order_items": 77,
        "int_returns": 11,
        "int_promotion_assignments": 13,
    }
    assert direct_rejections_remaining == 0
    assert business_rule_failures == 0
    assert return_rule_failures == 0
    assert reconciliation_failures == 0
    assert rejected_lineage[0] > 0
    assert rejected_lineage == (rejected_lineage[0],) * 4


def test_dbt_intermediate_resolves_parents_within_the_same_load(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    clean_config = replace(
        configured,
        customer_count=10,
        error_rates={name: 0.0 for name in configured.error_rates},
    )
    invalid_config = replace(
        clean_config,
        error_rates={name: 0.01 for name in configured.error_rates},
    )
    clean_dataset = generate_dataset(clean_config)
    invalid_dataset = generate_dataset(invalid_config)
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        for dataset, load_id in (
            (clean_dataset, "clean-load"),
            (invalid_dataset, "invalid-load"),
        ):
            ingest_to_bronze(
                dataset,
                validate_sources(dataset, load_id=load_id),
                connection,
                load_id=load_id,
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
    staging_result = dbtRunner().invoke(["run", "--select", "staging", *common_args])
    intermediate_result = dbtRunner().invoke(
        ["build", "--select", "intermediate", *common_args]
    )

    assert staging_result.success, staging_result.exception
    assert intermediate_result.success, intermediate_result.exception
    with duckdb.connect(str(warehouse_path)) as connection:
        invalid_load_counts = {
            model: connection.execute(
                f"""
                SELECT count(*)
                FROM silver.{model}
                WHERE _load_id = 'invalid-load'
                """
            ).fetchone()[0]
            for model in (
                "int_orders",
                "int_order_items",
                "int_returns",
                "int_promotion_assignments",
            )
        }
        historical_rows = connection.execute(
            """
            SELECT count(*)
            FROM (
                SELECT _load_id FROM silver.int_customers
                UNION ALL SELECT _load_id FROM silver.int_products
                UNION ALL SELECT _load_id FROM silver.int_orders
                UNION ALL SELECT _load_id FROM silver.int_order_items
                UNION ALL SELECT _load_id FROM silver.int_returns
                UNION ALL SELECT _load_id FROM silver.int_promotions
                UNION ALL SELECT _load_id FROM silver.int_promotion_assignments
                UNION ALL SELECT load_id FROM silver.int_rejected_records
            ) current_snapshot
            WHERE _load_id <> 'invalid-load'
            """
        ).fetchone()[0]

    assert invalid_load_counts == {
        "int_orders": 42,
        "int_order_items": 77,
        "int_returns": 11,
        "int_promotion_assignments": 13,
    }
    assert historical_rows == 0
