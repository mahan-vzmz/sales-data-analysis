from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

import pandas as pd

from sales_analytics.generation.generator import (
    GeneratorConfig,
    generate_dataset,
)
from sales_analytics.ingestion.validate import validate_sources

PROJECT_ROOT = Path(__file__).parents[2]
REPORT_COLUMNS = (
    "load_id",
    "source_table",
    "source_row",
    "check_name",
    "column_name",
    "failure_case",
)
SOURCE_TABLES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "returns",
    "promotions",
    "calendar_events",
)


def _config(error_rate: float) -> GeneratorConfig:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    return replace(
        configured,
        error_rates={name: error_rate for name in configured.error_rates},
    )


def test_validation_aggregates_multiple_failures_in_one_run() -> None:
    clean = generate_dataset(_config(error_rate=0.0))
    invalid_orders = clean.orders.copy()
    invalid_orders.loc[0, "payment_method"] = None
    invalid_orders.loc[1, "order_timestamp"] = pd.Timestamp("2026-01-01")
    invalid = replace(clean, orders=invalid_orders)

    result = validate_sources(invalid, load_id="load-multiple-errors")
    order_failures = result.failure_cases.loc[
        result.failure_cases["source_table"] == "orders"
    ]

    assert tuple(result.failure_cases.columns) == REPORT_COLUMNS
    assert set(order_failures["source_row"].dropna().astype(int)) == {0, 1}
    assert set(order_failures["check_name"]) >= {
        "not_nullable",
        "order_timestamp_in_range",
    }
    assert 0 not in result.valid_candidates["orders"].index
    assert 1 not in result.valid_candidates["orders"].index


def test_validation_preserves_check_names_when_rules_share_an_error() -> None:
    clean = generate_dataset(_config(error_rate=0.0))
    invalid_products = clean.products.copy()
    invalid_products.loc[0, "base_price"] = -1.0
    invalid_items = clean.order_items.copy()
    invalid_items.loc[0, "quantity"] = 0
    invalid = replace(
        clean,
        products=invalid_products,
        order_items=invalid_items,
    )

    result = validate_sources(invalid, load_id="load-check-names")
    actual = {
        (row.source_table, int(cast(float, row.source_row)), row.check_name)
        for row in result.failure_cases.itertuples()
        if pd.notna(row.source_row)
    }

    assert ("products", 0, "base_price_positive") in actual
    assert ("order_items", 0, "quantity_positive") in actual


def test_empty_returns_are_a_valid_source_batch() -> None:
    config = _config(error_rate=0.0)
    no_returns = replace(
        config,
        patterns=replace(config.patterns, return_probability=0.0),
    )
    dataset = generate_dataset(no_returns)

    result = validate_sources(dataset, load_id="load-no-returns")
    return_failures = result.failure_cases.loc[
        result.failure_cases["source_table"] == "returns"
    ]
    return_summary = result.summary.loc[
        result.summary["source_table"] == "returns"
    ].iloc[0]

    assert dataset.returns.empty
    assert return_failures.empty
    assert result.valid_candidates["returns"].empty
    assert return_summary["invalid_rows"] == 0


def test_missing_reference_column_is_reported_without_child_cascade() -> None:
    clean = generate_dataset(_config(error_rate=0.0))
    invalid = replace(clean, orders=clean.orders.drop(columns="order_id"))

    result = validate_sources(invalid, load_id="load-missing-reference")

    assert (
        (result.failure_cases["source_table"] == "orders")
        & (result.failure_cases["column_name"] == "order_id")
        & (result.failure_cases["check_name"] == "column_in_dataframe")
    ).any()
    assert not (
        (result.failure_cases["source_table"] == "order_items")
        & (result.failure_cases["check_name"] == "order_id_foreign_key")
    ).any()


def test_wrong_reference_dtype_is_reported_without_validator_crash() -> None:
    clean = generate_dataset(_config(error_rate=0.0))
    invalid_orders = clean.orders.copy()
    invalid_orders["order_timestamp"] = invalid_orders["order_timestamp"].astype(str)
    invalid = replace(clean, orders=invalid_orders)

    result = validate_sources(invalid, load_id="load-wrong-reference-dtype")
    order_failures = result.failure_cases.loc[
        (result.failure_cases["source_table"] == "orders")
        & (result.failure_cases["column_name"] == "order_timestamp")
    ]

    assert not order_failures.empty
    assert order_failures["check_name"].str.startswith("dtype(").any()


def test_cross_column_rule_produces_one_focused_finding() -> None:
    clean = generate_dataset(_config(error_rate=0.0))
    invalid_items = clean.order_items.copy()
    unit_price = cast(float, invalid_items.loc[0, "unit_price"])
    invalid_items.loc[0, "unit_cost"] = unit_price + 0.01
    invalid = replace(clean, order_items=invalid_items)

    result = validate_sources(invalid, load_id="load-cross-column")
    findings = result.failure_cases.loc[
        (result.failure_cases["source_table"] == "order_items")
        & (result.failure_cases["check_name"] == "unit_cost_lte_unit_price")
    ]

    assert len(findings) == 1
    assert findings.iloc[0]["source_row"] == 0
    assert findings.iloc[0]["column_name"] == "unit_cost,unit_price"


def test_validation_report_reconciles_exactly_with_generator_truth() -> None:
    dataset = generate_dataset(_config(error_rate=0.01))

    result = validate_sources(dataset, load_id="load-reconciliation")

    expected_invalid = {
        tuple(issue_id.split(":"))
        for ids_for_type in dataset.truth.issue_ids.values()
        for issue_id in ids_for_type
    }
    actual_invalid = {
        (str(row.source_table), str(int(cast(float, row.source_row))))
        for row in result.failure_cases.itertuples()
        if pd.notna(row.source_row)
    }

    assert actual_invalid == expected_invalid
    assert set(result.failure_cases["load_id"]) == {"load-reconciliation"}
    assert "order_id_foreign_key" in set(result.failure_cases["check_name"])
    assert result.failure_cases["check_name"].str.len().max() < 80

    for table_name in SOURCE_TABLES:
        source = getattr(dataset, table_name)
        rejected_rows = {
            int(source_row)
            for source_table, source_row in expected_invalid
            if source_table == table_name
        }
        assert set(result.valid_candidates[table_name].index) == (
            set(source.index) - rejected_rows
        )

    assert result.summary["invalid_rows"].sum() == len(expected_invalid)
    assert result.summary["valid_rows"].sum() + len(expected_invalid) == sum(
        len(getattr(dataset, table_name)) for table_name in SOURCE_TABLES
    )
