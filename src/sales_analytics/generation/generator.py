"""Deterministic normalized retail dataset generator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from math import isfinite
from pathlib import Path
from random import Random
from typing import cast

import pandas as pd

from sales_analytics.generation.patterns import (
    calendar_dates,
    promotion_dates,
    weighted_order_date,
)

ISSUE_TYPES = (
    "duplicate_id",
    "null_required_field",
    "invalid_price_or_cost",
    "out_of_range_date",
    "excess_return_quantity",
    "broken_foreign_key",
)


def _json_mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{name} must be a JSON object")
    return cast(dict[str, object], value)


def _json_list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    return cast(list[object], value)


def _json_int(mapping: dict[str, object], name: str) -> int:
    value = mapping.get(name)
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return value


def _json_number(mapping: dict[str, object], name: str) -> float:
    value = mapping.get(name)
    if type(value) not in (int, float) or not isfinite(cast(float, value)):
        raise ValueError(f"{name} must be a finite number")
    return float(cast(float, value))


def _json_string(mapping: dict[str, object], name: str) -> str:
    value = mapping.get(name)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _json_int_tuple(
    mapping: dict[str, object], name: str, length: int | None = None
) -> tuple[int, ...]:
    values = _json_list(mapping.get(name), name)
    if length is not None and len(values) != length:
        raise ValueError(f"{name} must contain {length} integers")
    if any(type(value) is not int for value in values):
        raise ValueError(f"{name} must contain integers")
    return tuple(cast(int, value) for value in values)


def _json_string_tuple(mapping: dict[str, object], name: str) -> tuple[str, ...]:
    values = _json_list(mapping.get(name), name)
    if any(not isinstance(value, str) for value in values):
        raise ValueError(f"{name} must contain strings")
    return tuple(cast(str, value) for value in values)


@dataclass(frozen=True)
class ProductConfig:
    """A product supplied through generator configuration."""

    product_id: str
    name: str
    category: str
    base_price: float
    base_cost: float


@dataclass(frozen=True)
class PatternConfig:
    """Tunable behavioral signals planted in otherwise random data."""

    orders_per_customer_year: int
    annual_order_growth: int
    inactive_customer_rate: float
    peak_months: tuple[int, ...]
    peak_weight: float
    promotion_weight: float
    promotion_window: tuple[tuple[int, int], tuple[int, int]]
    promotion_discount_rate: float
    channel_weights: dict[str, float]
    affinity_probability: float
    affinity_source_product_ids: tuple[str, ...]
    affinity_target_product_id: str
    items_per_order: tuple[int, int]
    return_probability: float
    full_return_probability: float

    def __post_init__(self) -> None:
        if (
            type(self.orders_per_customer_year) is not int
            or type(self.annual_order_growth) is not int
        ):
            raise ValueError("order counts must be integers")
        probabilities = (
            self.inactive_customer_rate,
            self.affinity_probability,
            self.return_probability,
            self.full_return_probability,
        )
        if any(
            not isfinite(value) or value < 0 or value > 1 for value in probabilities
        ):
            raise ValueError("pattern probabilities must be between zero and one")
        if self.orders_per_customer_year < 1 or self.annual_order_growth < 0:
            raise ValueError("order counts must be non-negative")
        if not self.peak_months or any(
            month not in range(1, 13) for month in self.peak_months
        ):
            raise ValueError("peak_months must contain valid calendar months")
        if (
            not isfinite(self.peak_weight)
            or not isfinite(self.promotion_weight)
            or self.peak_weight <= 0
            or self.promotion_weight <= 0
        ):
            raise ValueError("date weights must be positive")
        promotion_start, promotion_end = promotion_dates(2000, self.promotion_window)
        if promotion_start > promotion_end:
            raise ValueError("promotion window must not cross the year boundary")
        if (
            not isfinite(self.promotion_discount_rate)
            or self.promotion_discount_rate < 0
            or self.promotion_discount_rate > 1
        ):
            raise ValueError("promotion discount rate must be between zero and one")
        if set(self.channel_weights) != {"Online", "Store", "Marketplace"}:
            raise ValueError("channel_weights must configure all supported channels")
        if any(weight <= 0 for weight in self.channel_weights.values()):
            raise ValueError("channel weights must be positive")
        minimum_items, maximum_items = self.items_per_order
        if minimum_items < 1 or maximum_items < minimum_items:
            raise ValueError("items_per_order must be a positive ordered range")
        if not self.affinity_source_product_ids:
            raise ValueError("affinity requires at least one source product")
        if self.affinity_target_product_id in self.affinity_source_product_ids:
            raise ValueError("affinity target must differ from its source products")
        if self.affinity_probability > 0 and maximum_items < 2:
            raise ValueError("affinity requires room for source and target products")


@dataclass(frozen=True)
class GeneratorConfig:
    """Inputs that fully determine a generated dataset."""

    start_date: date
    end_date: date
    seed: int
    customer_count: int
    patterns: PatternConfig
    product_catalog: tuple[ProductConfig, ...]
    error_rates: dict[str, float]

    def __post_init__(self) -> None:
        if type(self.seed) is not int or type(self.customer_count) is not int:
            raise ValueError("seed and customer_count must be integers")
        if self.start_date.month != 1 or self.start_date.day != 1:
            raise ValueError("start_date must be the first day of a calendar year")
        if self.end_date.month != 12 or self.end_date.day != 31:
            raise ValueError("end_date must be the last day of a calendar year")

        year_count = self.end_date.year - self.start_date.year + 1
        if year_count not in range(3, 6):
            raise ValueError("date range must contain three to five complete years")
        if self.customer_count < 1:
            raise ValueError("customer_count must be positive")
        if not self.product_catalog:
            raise ValueError("product_catalog must not be empty")

        product_ids = [product.product_id for product in self.product_catalog]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("product IDs must be unique")
        if any(
            not isfinite(rate) or rate < 0 or rate > 1
            for rate in self.error_rates.values()
        ):
            raise ValueError("error rates must be between zero and one")
        if set(self.error_rates) != set(ISSUE_TYPES):
            raise ValueError("error_rates must configure every supported issue type")
        try:
            for year in range(self.start_date.year, self.end_date.year + 1):
                promotion_dates(year, self.patterns.promotion_window)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "promotion window must be valid for every generated year"
            ) from error
        affinity_ids = {
            *self.patterns.affinity_source_product_ids,
            self.patterns.affinity_target_product_id,
        }
        if not affinity_ids <= set(product_ids):
            raise ValueError("affinity products must exist in product_catalog")
        if self.patterns.items_per_order[1] > len(self.product_catalog):
            raise ValueError("items_per_order cannot exceed the product catalog")

    @classmethod
    def from_json(cls, path: Path) -> GeneratorConfig:
        """Load a generator configuration from a JSON fixture."""
        payload = _json_mapping(json.loads(path.read_text(encoding="utf-8")), "config")
        raw_catalog = [
            _json_mapping(product, f"product_catalog[{index}]")
            for index, product in enumerate(
                _json_list(payload.get("product_catalog"), "product_catalog")
            )
        ]
        raw_error_rates = _json_mapping(payload.get("error_rates"), "error_rates")
        raw_patterns = _json_mapping(payload.get("patterns"), "patterns")
        raw_channel_weights = _json_mapping(
            raw_patterns.get("channel_weights"), "channel_weights"
        )
        raw_promotion_window = _json_list(
            raw_patterns.get("promotion_window"), "promotion_window"
        )
        if len(raw_promotion_window) != 2:
            raise ValueError("promotion_window must contain two month/day pairs")
        promotion_window = tuple(
            _json_int_tuple({"value": value}, "value", length=2)
            for value in raw_promotion_window
        )
        items_per_order = _json_int_tuple(raw_patterns, "items_per_order", length=2)

        return cls(
            start_date=date.fromisoformat(_json_string(payload, "start_date")),
            end_date=date.fromisoformat(_json_string(payload, "end_date")),
            seed=_json_int(payload, "seed"),
            customer_count=_json_int(payload, "customer_count"),
            patterns=PatternConfig(
                orders_per_customer_year=_json_int(
                    raw_patterns, "orders_per_customer_year"
                ),
                annual_order_growth=_json_int(raw_patterns, "annual_order_growth"),
                inactive_customer_rate=_json_number(
                    raw_patterns, "inactive_customer_rate"
                ),
                peak_months=_json_int_tuple(raw_patterns, "peak_months"),
                peak_weight=_json_number(raw_patterns, "peak_weight"),
                promotion_weight=_json_number(raw_patterns, "promotion_weight"),
                promotion_window=(
                    (promotion_window[0][0], promotion_window[0][1]),
                    (promotion_window[1][0], promotion_window[1][1]),
                ),
                promotion_discount_rate=_json_number(
                    raw_patterns, "promotion_discount_rate"
                ),
                channel_weights={
                    name: _json_number(raw_channel_weights, name)
                    for name in raw_channel_weights
                },
                affinity_probability=_json_number(raw_patterns, "affinity_probability"),
                affinity_source_product_ids=_json_string_tuple(
                    raw_patterns, "affinity_source_product_ids"
                ),
                affinity_target_product_id=_json_string(
                    raw_patterns, "affinity_target_product_id"
                ),
                items_per_order=(
                    items_per_order[0],
                    items_per_order[1],
                ),
                return_probability=_json_number(raw_patterns, "return_probability"),
                full_return_probability=_json_number(
                    raw_patterns, "full_return_probability"
                ),
            ),
            product_catalog=tuple(
                ProductConfig(
                    product_id=_json_string(product, "product_id"),
                    name=_json_string(product, "name"),
                    category=_json_string(product, "category"),
                    base_price=_json_number(product, "base_price"),
                    base_cost=_json_number(product, "base_cost"),
                )
                for product in raw_catalog
            ),
            error_rates={
                name: _json_number(raw_error_rates, name) for name in raw_error_rates
            },
        )


@dataclass(frozen=True)
class TruthMetadata:
    """Known facts about one generated dataset."""

    seed: int
    start_date: date
    end_date: date
    row_counts: dict[str, int]
    issue_counts: dict[str, int]
    issue_ids: dict[str, tuple[str, ...]]
    pattern_parameters: dict[str, object]


@dataclass(frozen=True)
class GeneratedDataset:
    """Normalized source tables plus their known truth."""

    customers: pd.DataFrame
    products: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    returns: pd.DataFrame
    promotions: pd.DataFrame
    calendar_events: pd.DataFrame
    truth: TruthMetadata


def generate_dataset(config: GeneratorConfig) -> GeneratedDataset:
    """Generate normalized retail data and then inject configured issues."""
    customer_random = Random(f"{config.seed}:customers")
    profile_random = Random(f"{config.seed}:profiles")
    date_random = Random(f"{config.seed}:dates")
    order_random = Random(f"{config.seed}:orders")
    basket_random = Random(f"{config.seed}:baskets")
    return_random = Random(f"{config.seed}:returns")
    years = range(config.start_date.year, config.end_date.year + 1)

    products = pd.DataFrame(
        [
            {
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "base_price": product.base_price,
                "base_cost": product.base_cost,
            }
            for product in config.product_catalog
        ]
    )
    promotions = pd.DataFrame(
        [
            {
                "promotion_id": f"PROMO-{year}",
                "promotion_type": "holiday",
                "start_date": promotion_dates(year, config.patterns.promotion_window)[
                    0
                ],
                "end_date": promotion_dates(year, config.patterns.promotion_window)[1],
                "discount_policy": config.patterns.promotion_discount_rate,
            }
            for year in years
        ]
    )

    customer_rows: list[dict[str, object]] = []
    for customer_number in range(1, config.customer_count + 1):
        customer_rows.append(
            {
                "customer_id": f"CUST-{customer_number:05d}",
                "signup_date": config.start_date
                - timedelta(days=customer_random.randint(0, 730)),
                "home_city": customer_random.choice(
                    ("Tehran", "Mashhad", "Shiraz", "Tabriz", "Isfahan")
                ),
                "segment": customer_random.choice(
                    ("Consumer", "Corporate", "Small Business")
                ),
            }
        )
    customers = pd.DataFrame(customer_rows)
    customer_ids = [cast(str, row["customer_id"]) for row in customer_rows]
    inactive_count = round(
        config.customer_count * config.patterns.inactive_customer_rate
    )
    inactive_ids = set(profile_random.sample(customer_ids, inactive_count))

    order_rows: list[dict[str, object]] = []
    item_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []
    order_number = 0
    line_number = 0
    channels = tuple(config.patterns.channel_weights)
    channel_weights = tuple(config.patterns.channel_weights.values())

    for customer in customer_rows:
        customer_id = cast(str, customer["customer_id"])
        for year_index, year in enumerate(years):
            if customer_id in inactive_ids:
                order_count = 1 if year_index == 0 else 0
            else:
                order_count = (
                    config.patterns.orders_per_customer_year
                    + year_index * config.patterns.annual_order_growth
                )

            for _ in range(order_count):
                order_number += 1
                order_date = weighted_order_date(
                    date_random,
                    year,
                    config.patterns.peak_months,
                    config.patterns.peak_weight,
                    config.patterns.promotion_weight,
                    config.patterns.promotion_window,
                )
                promotion_start, promotion_end = promotion_dates(
                    year, config.patterns.promotion_window
                )
                promotion_id = (
                    f"PROMO-{year}"
                    if promotion_start <= order_date <= promotion_end
                    else None
                )
                order_id = f"ORD-{order_number:07d}"
                order_rows.append(
                    {
                        "order_id": order_id,
                        "customer_id": customer_id,
                        "order_timestamp": datetime.combine(
                            order_date,
                            time(
                                hour=order_random.randint(8, 21),
                                minute=order_random.randint(0, 59),
                            ),
                        ),
                        "channel": order_random.choices(
                            channels, weights=channel_weights, k=1
                        )[0],
                        "payment_method": order_random.choice(
                            ("Credit Card", "Debit Card", "Digital Wallet")
                        ),
                        "promotion_id": promotion_id,
                    }
                )

                selected_products = _select_products(config, basket_random)
                for product in selected_products:
                    line_number += 1
                    quantity = basket_random.randint(1, 4)
                    line_id = f"LINE-{line_number:08d}"
                    item_rows.append(
                        {
                            "line_id": line_id,
                            "order_id": order_id,
                            "product_id": product.product_id,
                            "quantity": quantity,
                            "unit_price": product.base_price,
                            "unit_cost": product.base_cost,
                            "discount_rate": config.patterns.promotion_discount_rate
                            if promotion_id
                            else 0.0,
                        }
                    )

                    if return_random.random() < config.patterns.return_probability:
                        is_full_return = (
                            quantity == 1
                            or return_random.random()
                            < config.patterns.full_return_probability
                        )
                        returned_quantity = (
                            quantity
                            if is_full_return
                            else return_random.randint(1, quantity - 1)
                        )
                        return_rows.append(
                            {
                                "return_id": f"RET-{len(return_rows) + 1:07d}",
                                "line_id": line_id,
                                "return_date": min(
                                    order_date
                                    + timedelta(days=return_random.randint(1, 30)),
                                    config.end_date,
                                ),
                                "returned_quantity": returned_quantity,
                                "reason": return_random.choice(
                                    ("Damaged", "Changed mind", "Wrong item")
                                ),
                            }
                        )

    orders = pd.DataFrame(order_rows)
    order_items = pd.DataFrame(item_rows)
    returns = pd.DataFrame(
        return_rows,
        columns=(
            "return_id",
            "line_id",
            "return_date",
            "returned_quantity",
            "reason",
        ),
    )
    if returns.empty:
        returns = returns.astype(
            {
                "return_id": str,
                "line_id": str,
                "returned_quantity": int,
                "reason": str,
            }
        )
    calendar_events = _build_calendar_events(
        config.start_date, config.end_date, config.patterns.promotion_window
    )

    tables = {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "returns": returns,
        "promotions": promotions,
        "calendar_events": calendar_events,
    }
    issue_ids = _inject_quality_issues(
        tables, config, Random(f"{config.seed}:quality-issues")
    )
    truth = TruthMetadata(
        seed=config.seed,
        start_date=config.start_date,
        end_date=config.end_date,
        row_counts={name: len(table) for name, table in tables.items()},
        issue_counts={name: len(ids) for name, ids in issue_ids.items()},
        issue_ids={name: tuple(ids) for name, ids in issue_ids.items()},
        pattern_parameters=cast(dict[str, object], asdict(config.patterns)),
    )

    return GeneratedDataset(
        customers=tables["customers"],
        products=tables["products"],
        orders=tables["orders"],
        order_items=tables["order_items"],
        returns=tables["returns"],
        promotions=tables["promotions"],
        calendar_events=tables["calendar_events"],
        truth=truth,
    )


def _select_products(config: GeneratorConfig, random: Random) -> list[ProductConfig]:
    item_count = random.randint(*config.patterns.items_per_order)
    selected = random.sample(list(config.product_catalog), item_count)
    source_ids = set(config.patterns.affinity_source_product_ids)
    mouse = next(
        (
            product
            for product in config.product_catalog
            if product.product_id == config.patterns.affinity_target_product_id
        ),
    )
    has_laptop = any(product.product_id in source_ids for product in selected)
    has_mouse = mouse in selected

    if (
        has_laptop
        and not has_mouse
        and random.random() < config.patterns.affinity_probability
    ):
        if len(selected) < config.patterns.items_per_order[1]:
            selected.append(mouse)
        else:
            replace_at = next(
                (
                    index
                    for index, product in enumerate(selected)
                    if product.product_id not in source_ids
                ),
                len(selected) - 1,
            )
            selected[replace_at] = mouse

    return selected


def _inject_quality_issues(
    tables: dict[str, pd.DataFrame], config: GeneratorConfig, random: Random
) -> dict[str, list[str]]:
    issue_ids: dict[str, list[str]] = {name: [] for name in ISSUE_TYPES}

    customers = tables["customers"]
    duplicate_count = _issue_count(config.error_rates["duplicate_id"], len(customers))
    if duplicate_count:
        original_indices = random.sample(range(len(customers)), duplicate_count)
        duplicate_rows = customers.iloc[original_indices].copy()
        first_new_index = len(customers)
        tables["customers"] = pd.concat((customers, duplicate_rows), ignore_index=True)
        new_indices = [
            index for index in range(first_new_index, first_new_index + duplicate_count)
        ]
        issue_ids["duplicate_id"] = [
            f"customers:{index}" for index in (*original_indices, *new_indices)
        ]

    orders = tables["orders"]
    returned_line_ids = set(tables["returns"]["line_id"])
    order_ids_with_returns = set(
        tables["order_items"].loc[
            tables["order_items"]["line_id"].isin(returned_line_ids), "order_id"
        ]
    )
    available_orders = list(range(len(orders)))
    random.shuffle(available_orders)
    null_count = _issue_count(config.error_rates["null_required_field"], len(orders))
    null_rows = _take_rows(
        available_orders,
        null_count,
        "null_required_field",
    )
    orders.loc[null_rows, "payment_method"] = pd.NA
    issue_ids["null_required_field"] = [f"orders:{index}" for index in null_rows]

    safe_date_rows = [
        index
        for index in available_orders
        if orders.at[index, "order_id"] not in order_ids_with_returns
        and pd.isna(orders.at[index, "promotion_id"])
    ]
    date_count = _issue_count(config.error_rates["out_of_range_date"], len(orders))
    out_of_range_rows = _take_rows(
        safe_date_rows,
        date_count,
        "out_of_range_date",
    )
    orders.loc[out_of_range_rows, "order_timestamp"] = datetime.combine(
        config.end_date + timedelta(days=1), time(hour=12)
    )
    issue_ids["out_of_range_date"] = [f"orders:{index}" for index in out_of_range_rows]

    products = tables["products"]
    invalid_rows = random.sample(
        range(len(products)),
        _available_issue_count(
            config.error_rates["invalid_price_or_cost"],
            len(products),
            len(products),
            "invalid_price_or_cost",
        ),
    )
    products.loc[invalid_rows, "base_price"] = -1.0
    issue_ids["invalid_price_or_cost"] = [f"products:{index}" for index in invalid_rows]

    returns = tables["returns"]
    excess_count = _available_issue_count(
        config.error_rates["excess_return_quantity"],
        len(returns),
        len(returns),
        "excess_return_quantity",
    )
    excess_rows = random.sample(
        range(len(returns)),
        excess_count,
    )
    quantity_by_line = {
        cast(str, row.line_id): cast(int, row.quantity)
        for row in tables["order_items"].itertuples()
    }
    for index in excess_rows:
        line_id = cast(str, returns.at[index, "line_id"])
        returns.at[index, "returned_quantity"] = quantity_by_line[line_id] + 1
    issue_ids["excess_return_quantity"] = [f"returns:{index}" for index in excess_rows]

    order_items = tables["order_items"]
    safe_line_rows = [
        index
        for index in range(len(order_items))
        if order_items.at[index, "line_id"] not in returned_line_ids
    ]
    broken_count = _available_issue_count(
        config.error_rates["broken_foreign_key"],
        len(order_items),
        len(safe_line_rows),
        "broken_foreign_key",
    )
    broken_rows = random.sample(
        safe_line_rows,
        broken_count,
    )
    for index in broken_rows:
        order_items.at[index, "order_id"] = f"MISSING-ORDER-{index:07d}"
    issue_ids["broken_foreign_key"] = [f"order_items:{index}" for index in broken_rows]

    return issue_ids


def _issue_count(rate: float, row_count: int) -> int:
    if rate == 0 or row_count == 0:
        return 0
    return min(row_count, max(1, round(rate * row_count)))


def _available_issue_count(
    rate: float,
    population: int,
    available: int,
    issue_name: str,
) -> int:
    if rate > 0 and population == 0:
        raise ValueError(f"not enough safe rows for {issue_name}")
    count = _issue_count(rate, population)
    if count > available:
        raise ValueError(f"not enough safe rows for {issue_name}")
    return count


def _take_rows(available: list[int], count: int, issue_name: str) -> list[int]:
    if count > len(available):
        raise ValueError(f"not enough safe rows for {issue_name}")
    selected = available[:count]
    del available[:count]
    return selected


def _build_calendar_events(
    start_date: date,
    end_date: date,
    promotion_window: tuple[tuple[int, int], tuple[int, int]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for event_date in calendar_dates(start_date, end_date):
        promotion_start, promotion_end = promotion_dates(
            event_date.year, promotion_window
        )
        in_campaign = promotion_start <= event_date <= promotion_end
        rows.append(
            {
                "date": event_date,
                "holiday": "New Year"
                if event_date.month == event_date.day == 1
                else None,
                "campaign": f"PROMO-{event_date.year}" if in_campaign else None,
                "seasonal_event": _season_name(event_date.month),
            }
        )
    return pd.DataFrame(rows)


def _season_name(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Autumn"
