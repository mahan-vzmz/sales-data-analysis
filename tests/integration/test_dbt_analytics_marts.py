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
MARTS = {
    "mart_executive",
    "mart_customer_360",
    "mart_cohort_base",
    "mart_basket_base",
    "mart_forecasting_base",
}


def test_dbt_analytics_marts_are_documented_and_reconcile_to_core(
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
            validate_sources(dataset, load_id="dbt-analytics"),
            connection,
            load_id="dbt-analytics",
        )

    monkeypatch.setenv("SALES_DUCKDB_PATH", str(warehouse_path))
    result = dbtRunner().invoke(
        [
            "build",
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
    manifest = json.loads((tmp_path / "target" / "manifest.json").read_text())
    mart_nodes = {
        node["name"]: node
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model" and node["name"] in MARTS
    }
    assert set(mart_nodes) == MARTS
    for node in mart_nodes.values():
        assert node["description"]
        assert node["meta"]["owner"] == "analytics_engineering"
        assert node["meta"]["grain"]
        assert node["columns"]
        assert all(column["description"] for column in node["columns"].values())
        direct_dependencies = set(node["depends_on"]["nodes"])
        assert direct_dependencies
        assert all(
            dependency.startswith(
                (
                    "model.sales_analytics.fact_",
                    "model.sales_analytics.dim_",
                    "model.sales_analytics.int_",
                )
            )
            for dependency in direct_dependencies
        )

    with duckdb.connect(str(warehouse_path)) as connection:
        mart_views = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'gold'
                  AND table_name LIKE 'mart_%'
                """
            ).fetchall()
        }
        mart_counts = {
            mart: connection.execute(f"SELECT count(*) FROM gold.{mart}").fetchone()[0]
            for mart in MARTS
        }
        executive_reconciliation = connection.execute(
            """
            SELECT count(*)
            FROM gold.mart_executive executive
            WHERE executive.sales_line_count
                    <> (SELECT count(*) FROM gold.fact_sales)
               OR executive.order_count
                    <> (SELECT count(DISTINCT order_id) FROM gold.fact_sales)
               OR executive.net_sales
                    <> (SELECT sum(net_sales) FROM gold.fact_sales)
               OR executive.returned_revenue
                    <> (SELECT sum(returned_revenue) FROM gold.fact_returns)
               OR executive.return_adjusted_revenue
                    <> executive.net_sales - executive.returned_revenue
               OR executive.return_adjusted_profit
                    <> (SELECT sum(gross_profit) FROM gold.fact_sales)
                       - (SELECT sum(profit_impact) FROM gold.fact_returns)
            """
        ).fetchone()[0]
        customer_reconciliation = connection.execute(
            """
            SELECT
                count(*) - count(DISTINCT customer_id),
                sum(net_sales),
                sum(returned_revenue),
                sum(return_adjusted_value)
            FROM gold.mart_customer_360
            """
        ).fetchone()
        fact_totals = connection.execute(
            """
            SELECT
                (SELECT sum(net_sales) FROM gold.fact_sales),
                (SELECT sum(returned_revenue) FROM gold.fact_returns),
                (SELECT sum(net_sales) FROM gold.fact_sales)
                    - (SELECT sum(returned_revenue) FROM gold.fact_returns)
            """
        ).fetchone()
        cohort_failures = connection.execute(
            """
            WITH order_quantities AS (
                SELECT order_id, sum(ordered_quantity) AS ordered_quantity
                FROM gold.fact_sales
                GROUP BY order_id
            ),
            returned_quantities AS (
                SELECT order_id, sum(returned_quantity) AS returned_quantity
                FROM gold.fact_returns
                GROUP BY order_id
            )
            SELECT count(*)
            FROM gold.mart_cohort_base cohort
            INNER JOIN order_quantities ordered USING (order_id)
            LEFT JOIN returned_quantities returned USING (order_id)
            WHERE coalesce(returned.returned_quantity, 0)
                >= ordered.ordered_quantity
            """
        ).fetchone()[0]
        basket_failures = connection.execute(
            """
            SELECT count(*)
            FROM gold.mart_basket_base
            WHERE remaining_quantity <= 0
            """
        ).fetchone()[0]
        forecasting_reconciliation = connection.execute(
            """
            SELECT
                sum(net_sales),
                sum(returned_revenue),
                sum(return_adjusted_revenue),
                count(*)
            FROM gold.mart_forecasting_base
            """
        ).fetchone()
        cross_week_returns = connection.execute(
            """
            SELECT count(*)
            FROM gold.fact_returns returns
            INNER JOIN gold.dim_date order_dates
                ON order_dates.date_key = returns.order_date_key
            INNER JOIN gold.dim_date return_dates
                ON return_dates.date_key = returns.return_date_key
            WHERE date_trunc('week', order_dates.full_date)
                <> date_trunc('week', return_dates.full_date)
            """
        ).fetchone()[0]
        forecast_order_week_failures = connection.execute(
            """
            WITH expected AS (
                SELECT
                    date_trunc('week', dates.full_date)::date AS week_start,
                    products.category,
                    sum(returns.returned_revenue) AS returned_revenue
                FROM gold.fact_returns returns
                INNER JOIN gold.dim_date dates
                    ON dates.date_key = returns.order_date_key
                INNER JOIN gold.dim_product products USING (product_id)
                GROUP BY week_start, products.category
            )
            SELECT count(*)
            FROM expected
            INNER JOIN gold.mart_forecasting_base actual
                USING (week_start, category)
            WHERE abs(expected.returned_revenue - actual.returned_revenue) > 0.01
            """
        ).fetchone()[0]
        forecast_grid_size = connection.execute(
            """
            SELECT
                count(DISTINCT date_trunc('week', full_date))
                    * (SELECT count(DISTINCT category) FROM gold.dim_product)
            FROM gold.dim_date
            """
        ).fetchone()[0]

    assert mart_views == MARTS
    assert mart_counts == {
        "mart_executive": 1,
        "mart_customer_360": 9,
        "mart_cohort_base": 39,
        "mart_basket_base": 68,
        "mart_forecasting_base": forecast_grid_size,
    }
    assert executive_reconciliation == 0
    assert customer_reconciliation == (0, *fact_totals)
    assert cohort_failures == 0
    assert basket_failures == 0
    assert cross_week_returns > 0
    assert forecast_order_week_failures == 0
    assert forecasting_reconciliation == (*fact_totals, forecast_grid_size)
