from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import cast

import pandas as pd
import pandera.pandas as pa
import pytest

from sales_analytics.generation.generator import (
    GeneratedDataset,
    GeneratorConfig,
    generate_dataset,
)
from sales_analytics.ingestion.contracts import build_source_schemas

SOURCE_TABLES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "returns",
    "promotions",
    "calendar_events",
)


@pytest.fixture(scope="module")
def clean_dataset() -> GeneratedDataset:
    project_root = Path(__file__).parents[3]
    configured = GeneratorConfig.from_json(
        project_root / "data" / "fixtures" / "generator_config.json"
    )
    config = replace(
        configured,
        customer_count=10,
        error_rates={name: 0.0 for name in configured.error_rates},
    )
    return generate_dataset(config)


def test_every_source_schema_accepts_valid_generated_data(
    clean_dataset: GeneratedDataset,
) -> None:
    schemas = build_source_schemas(clean_dataset)

    assert set(schemas) == set(SOURCE_TABLES)
    for table_name in SOURCE_TABLES:
        table = getattr(clean_dataset, table_name)
        validated = schemas[table_name].validate(table, lazy=True)
        pd.testing.assert_frame_equal(validated, table)


@pytest.mark.parametrize(
    ("table_name", "column_name"),
    (
        ("customers", "home_city"),
        ("products", "base_price"),
        ("orders", "payment_method"),
        ("order_items", "quantity"),
        ("returns", "returned_quantity"),
        ("promotions", None),
        ("calendar_events", "date"),
    ),
)
def test_each_source_schema_rejects_an_invalid_example(
    clean_dataset: GeneratedDataset,
    table_name: str,
    column_name: str | None,
) -> None:
    schemas = build_source_schemas(clean_dataset)
    invalid = getattr(clean_dataset, table_name).copy()

    if table_name == "customers":
        invalid.loc[0, "home_city"] = None
    elif table_name == "products":
        invalid.loc[0, "base_price"] = -1.0
    elif table_name == "orders":
        invalid.loc[0, "payment_method"] = None
    elif table_name == "order_items":
        invalid.loc[0, "quantity"] = 0
    elif table_name == "returns":
        invalid.loc[0, "returned_quantity"] = 0
    elif table_name == "promotions":
        invalid.loc[0, "end_date"] = invalid.loc[0, "start_date"] - pd.Timedelta(days=1)
    else:
        invalid.loc[1, "date"] = invalid.loc[0, "date"]

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schemas[table_name].validate(invalid, lazy=True)

    if column_name is not None:
        assert column_name in set(captured.value.failure_cases["column"].dropna())


@pytest.mark.parametrize(
    ("table_name", "required_column"),
    (
        ("customers", "customer_id"),
        ("products", "product_id"),
        ("orders", "order_id"),
        ("order_items", "line_id"),
        ("returns", "return_id"),
        ("promotions", "promotion_id"),
        ("calendar_events", "date"),
    ),
)
def test_every_schema_rejects_a_missing_required_column(
    clean_dataset: GeneratedDataset,
    table_name: str,
    required_column: str,
) -> None:
    schema = build_source_schemas(clean_dataset)[table_name]
    invalid = getattr(clean_dataset, table_name).drop(columns=required_column)

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schema.validate(invalid, lazy=True)

    assert "column_in_dataframe" in set(captured.value.failure_cases["check"])


@pytest.mark.parametrize(
    ("table_name", "identifier"),
    (
        ("customers", "customer_id"),
        ("products", "product_id"),
        ("orders", "order_id"),
        ("order_items", "line_id"),
        ("returns", "return_id"),
        ("promotions", "promotion_id"),
        ("calendar_events", "date"),
    ),
)
def test_every_schema_rejects_duplicate_identifiers(
    clean_dataset: GeneratedDataset,
    table_name: str,
    identifier: str,
) -> None:
    schema = build_source_schemas(clean_dataset)[table_name]
    invalid = getattr(clean_dataset, table_name).copy()
    invalid.loc[1, identifier] = invalid.loc[0, identifier]

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schema.validate(invalid, lazy=True)

    assert "field_uniqueness" in set(captured.value.failure_cases["check"])


@pytest.mark.parametrize(
    ("table_name", "column_name", "bad_value"),
    (
        ("products", "base_price", "not-a-number"),
        ("orders", "order_timestamp", "not-a-timestamp"),
    ),
)
def test_schemas_reject_wrong_dtypes(
    clean_dataset: GeneratedDataset,
    table_name: str,
    column_name: str,
    bad_value: str,
) -> None:
    schema = build_source_schemas(clean_dataset)[table_name]
    invalid = getattr(clean_dataset, table_name).copy()
    invalid[column_name] = invalid[column_name].astype(object)
    invalid.loc[0, column_name] = bad_value

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schema.validate(invalid, lazy=True)

    assert f"dtype('{schema.columns[column_name].dtype}')" in set(
        captured.value.failure_cases["check"]
    )


def test_required_values_are_not_nullable(clean_dataset: GeneratedDataset) -> None:
    schema = build_source_schemas(clean_dataset)["customers"]
    invalid = clean_dataset.customers.copy()
    invalid.loc[0, "home_city"] = None

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schema.validate(invalid, lazy=True)

    assert "not_nullable" in set(captured.value.failure_cases["check"])


def test_order_item_cost_cannot_exceed_price(
    clean_dataset: GeneratedDataset,
) -> None:
    schema = build_source_schemas(clean_dataset)["order_items"]
    invalid = clean_dataset.order_items.copy()
    unit_price = cast(float, invalid.loc[0, "unit_price"])
    invalid.loc[0, "unit_cost"] = unit_price + 0.01

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schema.validate(invalid, lazy=True)

    assert "unit_cost_lte_unit_price" in set(captured.value.failure_cases["check"])


@pytest.mark.parametrize(
    ("table_name", "column_name", "expected_check"),
    (
        ("customers", "signup_date", "signup_date_on_or_before_batch_end"),
        ("promotions", "start_date", "promotion_start_date_in_range"),
        ("promotions", "end_date", "promotion_end_date_in_range"),
        ("calendar_events", "date", "calendar_date_in_range"),
    ),
)
def test_batch_date_boundaries_are_enforced(
    clean_dataset: GeneratedDataset,
    table_name: str,
    column_name: str,
    expected_check: str,
) -> None:
    schema = build_source_schemas(clean_dataset)[table_name]
    invalid = getattr(clean_dataset, table_name).copy()
    invalid.loc[0, column_name] = clean_dataset.truth.end_date + timedelta(days=1)

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schema.validate(invalid, lazy=True)

    assert expected_check in set(captured.value.failure_cases["check"])


def test_return_date_must_follow_its_order_and_stay_in_batch(
    clean_dataset: GeneratedDataset,
) -> None:
    schema = build_source_schemas(clean_dataset)["returns"]
    invalid = clean_dataset.returns.copy()
    line_to_order = clean_dataset.order_items.set_index("line_id")["order_id"]
    order_dates = clean_dataset.orders.set_index("order_id")["order_timestamp"].dt.date
    first_line = invalid.loc[0, "line_id"]
    first_order = line_to_order[first_line]
    invalid.loc[0, "return_date"] = order_dates[first_order] - timedelta(days=1)
    invalid.loc[1, "return_date"] = clean_dataset.truth.end_date + timedelta(days=1)

    with pytest.raises(pa.errors.SchemaErrors) as captured:
        schema.validate(invalid, lazy=True)

    assert set(captured.value.failure_cases["check"]) >= {
        "return_date_on_or_after_order",
        "return_date_on_or_before_batch_end",
    }
