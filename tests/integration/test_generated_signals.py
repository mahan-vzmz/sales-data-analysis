from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from sales_analytics.generation.generator import (
    GeneratedDataset,
    GeneratorConfig,
    generate_dataset,
)

PROJECT_ROOT = Path(__file__).parents[2]
TABLE_NAMES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "returns",
    "promotions",
    "calendar_events",
)
ISSUE_TYPES = (
    "duplicate_id",
    "null_required_field",
    "invalid_price_or_cost",
    "out_of_range_date",
    "excess_return_quantity",
    "broken_foreign_key",
)


def _config(seed: int, error_rate: float = 0.0) -> GeneratorConfig:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    return replace(
        configured,
        seed=seed,
        customer_count=200,
        error_rates={issue_name: error_rate for issue_name in ISSUE_TYPES},
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


@pytest.fixture(scope="module", params=(7, 42, 99))
def clean_dataset(request: pytest.FixtureRequest) -> GeneratedDataset:
    return generate_dataset(_config(request.param))


def test_peak_season_revenue_exceeds_baseline_season(
    clean_dataset: GeneratedDataset,
) -> None:
    orders = clean_dataset.orders[["order_id", "order_timestamp"]].copy()
    orders["month"] = orders["order_timestamp"].dt.month
    lines = clean_dataset.order_items.copy()
    lines["revenue"] = (
        lines["quantity"] * lines["unit_price"] * (1.0 - lines["discount_rate"])
    )
    revenue = lines.merge(orders, on="order_id")

    peak = revenue.loc[revenue["month"].isin((10, 11, 12)), "revenue"].sum()
    baseline = revenue.loc[revenue["month"].isin((4, 5, 6)), "revenue"].sum()

    assert peak > baseline * 1.35


def test_order_volume_has_positive_annual_trend(
    clean_dataset: GeneratedDataset,
) -> None:
    yearly_orders = clean_dataset.orders["order_timestamp"].dt.year.value_counts()

    assert yearly_orders[2023] < yearly_orders[2024] < yearly_orders[2025]


def test_promotion_window_purchase_rate_exceeds_control_window(
    clean_dataset: GeneratedDataset,
) -> None:
    order_dates = clean_dataset.orders["order_timestamp"].dt.date
    in_promotion = clean_dataset.orders["promotion_id"].notna()
    in_control = order_dates.map(
        lambda value: date(value.year, 9, 15) <= value <= date(value.year, 10, 15)
    )

    assert int(in_promotion.sum()) > int(in_control.sum()) * 2

    promotion_order_ids = set(clean_dataset.orders.loc[in_promotion, "order_id"])
    promotion_discounts = clean_dataset.order_items.loc[
        clean_dataset.order_items["order_id"].isin(promotion_order_ids),
        "discount_rate",
    ]
    control_order_ids = set(clean_dataset.orders.loc[in_control, "order_id"])
    control_discounts = clean_dataset.order_items.loc[
        clean_dataset.order_items["order_id"].isin(control_order_ids),
        "discount_rate",
    ]

    assert (promotion_discounts == 0.10).all()
    assert (control_discounts == 0.0).all()


def test_channel_mix_uses_configured_ordering(
    clean_dataset: GeneratedDataset,
) -> None:
    channel_share = clean_dataset.orders["channel"].value_counts(normalize=True)

    assert channel_share["Online"] > channel_share["Store"]
    assert channel_share["Store"] > channel_share["Marketplace"]


def test_laptop_orders_have_mouse_affinity(
    clean_dataset: GeneratedDataset,
) -> None:
    baskets = clean_dataset.order_items.groupby("order_id")["product_id"].agg(set)
    has_laptop = baskets.map(lambda products: bool(products & {"PROD-001", "PROD-002"}))
    has_mouse = baskets.map(lambda products: "PROD-003" in products)

    mouse_with_laptop = float(has_mouse[has_laptop].mean())
    mouse_without_laptop = float(has_mouse[~has_laptop].mean())

    assert mouse_with_laptop > mouse_without_laptop * 2


def test_repeat_and_inactive_customers_both_exist(
    clean_dataset: GeneratedDataset,
) -> None:
    orders_per_customer = clean_dataset.orders["customer_id"].value_counts()
    inactive_ids = set(orders_per_customer[orders_per_customer == 1].index)
    inactive_order_years = clean_dataset.orders.loc[
        clean_dataset.orders["customer_id"].isin(inactive_ids), "order_timestamp"
    ].dt.year

    assert inactive_ids
    assert (inactive_order_years == clean_dataset.truth.start_date.year).all()
    assert (orders_per_customer > 1).any()


def test_partial_and_complete_returns_both_exist(
    clean_dataset: GeneratedDataset,
) -> None:
    returned_lines = clean_dataset.returns.merge(
        clean_dataset.order_items[["line_id", "quantity"]], on="line_id"
    )

    assert (returned_lines["returned_quantity"] < returned_lines["quantity"]).any()
    assert (returned_lines["returned_quantity"] == returned_lines["quantity"]).any()


def test_truth_records_all_pattern_parameters(
    clean_dataset: GeneratedDataset,
) -> None:
    assert {
        "annual_order_growth",
        "channel_weights",
        "affinity_probability",
        "inactive_customer_rate",
        "peak_months",
        "peak_weight",
        "promotion_weight",
        "promotion_window",
        "promotion_discount_rate",
        "affinity_source_product_ids",
        "affinity_target_product_id",
        "items_per_order",
        "return_probability",
        "full_return_probability",
    } <= clean_dataset.truth.pattern_parameters.keys()


def test_pattern_parameter_changes_generated_behavior() -> None:
    base = _config(seed=42)
    higher_discount = replace(
        base,
        patterns=replace(base.patterns, promotion_discount_rate=0.25),
    )

    dataset = generate_dataset(higher_discount)
    promotion_order_ids = set(
        dataset.orders.loc[dataset.orders["promotion_id"].notna(), "order_id"]
    )
    promotion_discounts = dataset.order_items.loc[
        dataset.order_items["order_id"].isin(promotion_order_ids), "discount_rate"
    ]

    assert (promotion_discounts == 0.25).all()


def test_quality_issues_are_controlled_and_non_overlapping() -> None:
    config = _config(seed=42, error_rate=0.01)
    dataset = generate_dataset(config)

    assert all(dataset.truth.issue_counts[name] > 0 for name in ISSUE_TYPES)

    issue_ids = [
        issue_id
        for ids_for_type in dataset.truth.issue_ids.values()
        for issue_id in ids_for_type
    ]
    assert len(issue_ids) == len(set(issue_ids))
    assert len(issue_ids) == sum(dataset.truth.issue_counts.values())

    duplicate_count = int(dataset.customers["customer_id"].duplicated(keep=False).sum())
    null_count = int(dataset.orders["payment_method"].isna().sum())
    invalid_count = int((dataset.products["base_price"] <= 0).sum())
    order_dates = dataset.orders["order_timestamp"].dt.date
    out_of_range_count = int(
        ((order_dates < config.start_date) | (order_dates > config.end_date)).sum()
    )
    returned_lines = dataset.returns.merge(
        dataset.order_items[["line_id", "quantity"]], on="line_id"
    )
    excess_return_count = int(
        (returned_lines["returned_quantity"] > returned_lines["quantity"]).sum()
    )
    broken_fk_count = int(
        (~dataset.order_items["order_id"].isin(dataset.orders["order_id"])).sum()
    )

    assert duplicate_count == dataset.truth.issue_counts["duplicate_id"]
    assert null_count == dataset.truth.issue_counts["null_required_field"]
    assert invalid_count == dataset.truth.issue_counts["invalid_price_or_cost"]
    assert out_of_range_count == dataset.truth.issue_counts["out_of_range_date"]
    assert excess_return_count == dataset.truth.issue_counts["excess_return_quantity"]
    assert broken_fk_count == dataset.truth.issue_counts["broken_foreign_key"]

    out_of_range_indices = {
        int(issue_id.split(":")[1])
        for issue_id in dataset.truth.issue_ids["out_of_range_date"]
    }
    out_of_range_order_ids = set(
        dataset.orders.loc[list(out_of_range_indices), "order_id"]
    )
    affected_line_ids = set(
        dataset.order_items.loc[
            dataset.order_items["order_id"].isin(out_of_range_order_ids), "line_id"
        ]
    )
    broken_indices = {
        int(issue_id.split(":")[1])
        for issue_id in dataset.truth.issue_ids["broken_foreign_key"]
    }
    broken_line_ids = set(dataset.order_items.loc[list(broken_indices), "line_id"])
    returned_line_ids = set(dataset.returns["line_id"])

    assert affected_line_ids.isdisjoint(returned_line_ids)
    assert broken_line_ids.isdisjoint(returned_line_ids)

    return_timeline = dataset.returns.merge(
        dataset.order_items[["line_id", "order_id"]], on="line_id"
    ).merge(dataset.orders[["order_id", "order_timestamp"]], on="order_id")
    assert (
        return_timeline["return_date"] >= return_timeline["order_timestamp"].dt.date
    ).all()


def test_dirty_generation_is_reproducible_and_seeded() -> None:
    config = _config(seed=42, error_rate=0.01)
    first = generate_dataset(config)
    second = generate_dataset(config)
    other_seed = generate_dataset(_config(seed=43, error_rate=0.01))

    assert _table_hashes(first) == _table_hashes(second)
    assert first.truth.issue_ids == second.truth.issue_ids
    assert first.truth.issue_ids != other_seed.truth.issue_ids


def test_injector_rejects_competing_rates_beyond_safe_capacity() -> None:
    base = _config(seed=42)
    rates = {name: 0.0 for name in ISSUE_TYPES}
    rates["null_required_field"] = 1.0
    rates["out_of_range_date"] = 1.0

    with pytest.raises(ValueError, match="enough safe rows"):
        generate_dataset(replace(base, error_rates=rates))


def test_injector_rejects_issue_without_eligible_rows() -> None:
    base = _config(seed=42)
    rates = {name: 0.0 for name in ISSUE_TYPES}
    rates["excess_return_quantity"] = 0.1
    no_returns = replace(
        base,
        patterns=replace(base.patterns, return_probability=0.0),
        error_rates=rates,
    )

    with pytest.raises(ValueError, match="enough safe rows"):
        generate_dataset(no_returns)
