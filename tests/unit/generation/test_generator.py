from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from sales_analytics.generation.generator import (
    GeneratedDataset,
    GeneratorConfig,
    generate_dataset,
)

TABLE_NAMES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "returns",
    "promotions",
    "calendar_events",
)

PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "line_id",
    "returns": "return_id",
    "promotions": "promotion_id",
    "calendar_events": "date",
}


@pytest.fixture
def config() -> GeneratorConfig:
    project_root = Path(__file__).parents[3]
    return GeneratorConfig.from_json(
        project_root / "data" / "fixtures" / "generator_config.json"
    )


def _table_hashes(dataset: GeneratedDataset) -> dict[str, str]:
    return {
        name: sha256(
            pd.util.hash_pandas_object(
                getattr(dataset, name), index=True
            ).values.tobytes()
        ).hexdigest()
        for name in TABLE_NAMES
    }


def test_generation_is_reproducible_and_seeded(config: GeneratorConfig) -> None:
    first = generate_dataset(config)
    second = generate_dataset(config)
    other_seed = generate_dataset(replace(config, seed=config.seed + 1))

    assert _table_hashes(first) == _table_hashes(second)
    assert _table_hashes(first) != _table_hashes(other_seed)


def test_generated_tables_have_unique_keys_and_valid_relationships(
    config: GeneratorConfig,
) -> None:
    dataset = generate_dataset(config)

    for table_name, primary_key in PRIMARY_KEYS.items():
        table = getattr(dataset, table_name)
        assert table[primary_key].notna().all()
        assert table[primary_key].is_unique

    assert set(dataset.orders["customer_id"]) <= set(dataset.customers["customer_id"])
    assert set(dataset.order_items["order_id"]) <= set(dataset.orders["order_id"])
    assert set(dataset.order_items["product_id"]) <= set(dataset.products["product_id"])
    assert set(dataset.returns["line_id"]) <= set(dataset.order_items["line_id"])
    assert set(dataset.orders["promotion_id"].dropna()) <= set(
        dataset.promotions["promotion_id"]
    )


def test_three_complete_years_and_truth_metadata(config: GeneratorConfig) -> None:
    dataset = generate_dataset(config)

    assert dataset.calendar_events["date"].iloc[0].isoformat() == "2023-01-01"
    assert dataset.calendar_events["date"].iloc[-1].isoformat() == "2025-12-31"
    assert len(dataset.calendar_events) == 1096
    assert dataset.truth.seed == config.seed
    assert dataset.truth.start_date == config.start_date
    assert dataset.truth.end_date == config.end_date
    assert dataset.truth.row_counts == {
        name: len(getattr(dataset, name)) for name in TABLE_NAMES
    }
    assert dataset.truth.issue_counts == {
        issue_name: 0 for issue_name in config.error_rates
    }
    assert dataset.truth.pattern_parameters["orders_per_customer_year"] == 1


def test_date_range_can_expand_to_five_years_via_config(
    config: GeneratorConfig,
) -> None:
    five_year_config = replace(
        config,
        end_date=config.end_date.replace(year=config.end_date.year + 2),
        customer_count=5,
    )

    dataset = generate_dataset(five_year_config)

    assert dataset.calendar_events["date"].iloc[-1].isoformat() == "2027-12-31"
    assert len(dataset.calendar_events) == 1826
