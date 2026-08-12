"""Deterministic normalized retail dataset generator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from random import Random
from typing import cast

import pandas as pd

from sales_analytics.generation.patterns import calendar_dates


@dataclass(frozen=True)
class ProductConfig:
    """A product supplied through generator configuration."""

    product_id: str
    name: str
    category: str
    base_price: float
    base_cost: float


@dataclass(frozen=True)
class GeneratorConfig:
    """Inputs that fully determine a generated dataset."""

    start_date: date
    end_date: date
    seed: int
    customer_count: int
    product_catalog: tuple[ProductConfig, ...]
    error_rates: dict[str, float]

    def __post_init__(self) -> None:
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
        if any(rate < 0 or rate > 1 for rate in self.error_rates.values()):
            raise ValueError("error rates must be between zero and one")

    @classmethod
    def from_json(cls, path: Path) -> GeneratorConfig:
        """Load a generator configuration from a JSON fixture."""
        payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        raw_catalog = cast(list[dict[str, object]], payload["product_catalog"])
        raw_error_rates = cast(dict[str, object], payload["error_rates"])

        return cls(
            start_date=date.fromisoformat(cast(str, payload["start_date"])),
            end_date=date.fromisoformat(cast(str, payload["end_date"])),
            seed=cast(int, payload["seed"]),
            customer_count=cast(int, payload["customer_count"]),
            product_catalog=tuple(
                ProductConfig(
                    product_id=cast(str, product["product_id"]),
                    name=cast(str, product["name"]),
                    category=cast(str, product["category"]),
                    base_price=float(cast(float, product["base_price"])),
                    base_cost=float(cast(float, product["base_cost"])),
                )
                for product in raw_catalog
            ),
            error_rates={
                name: float(cast(float, rate)) for name, rate in raw_error_rates.items()
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


TABLE_NAMES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "returns",
    "promotions",
    "calendar_events",
)


def generate_dataset(config: GeneratorConfig) -> GeneratedDataset:
    """Generate valid normalized retail data determined entirely by config."""
    random = Random(config.seed)
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
                "start_date": date(year, 11, 15),
                "end_date": date(year, 12, 15),
                "discount_policy": 0.10,
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
                - timedelta(days=random.randint(0, 730)),
                "home_city": random.choice(
                    ("Tehran", "Mashhad", "Shiraz", "Tabriz", "Isfahan")
                ),
                "segment": random.choice(("Consumer", "Corporate", "Small Business")),
            }
        )
    customers = pd.DataFrame(customer_rows)

    order_rows: list[dict[str, object]] = []
    item_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []
    order_number = 0
    line_number = 0

    for customer in customer_rows:
        for year in years:
            order_number += 1
            first_day = date(year, 1, 1)
            last_day = date(year, 12, 31)
            order_date = first_day + timedelta(
                days=random.randint(0, (last_day - first_day).days)
            )
            promotion_id = (
                f"PROMO-{year}"
                if date(year, 11, 15) <= order_date <= date(year, 12, 15)
                else None
            )
            order_id = f"ORD-{order_number:07d}"
            order_rows.append(
                {
                    "order_id": order_id,
                    "customer_id": customer["customer_id"],
                    "order_timestamp": datetime.combine(
                        order_date,
                        time(hour=random.randint(8, 21), minute=random.randint(0, 59)),
                    ),
                    "channel": random.choice(("Online", "Store", "Marketplace")),
                    "payment_method": random.choice(
                        ("Credit Card", "Debit Card", "Digital Wallet")
                    ),
                    "promotion_id": promotion_id,
                }
            )

            item_count = random.randint(1, min(3, len(config.product_catalog)))
            for product in random.sample(config.product_catalog, item_count):
                line_number += 1
                quantity = random.randint(1, 4)
                line_id = f"LINE-{line_number:08d}"
                item_rows.append(
                    {
                        "line_id": line_id,
                        "order_id": order_id,
                        "product_id": product.product_id,
                        "quantity": quantity,
                        "unit_price": product.base_price,
                        "unit_cost": product.base_cost,
                        "discount_rate": 0.10 if promotion_id else 0.0,
                    }
                )

                if random.random() < 0.08:
                    return_rows.append(
                        {
                            "return_id": f"RET-{len(return_rows) + 1:07d}",
                            "line_id": line_id,
                            "return_date": min(
                                order_date + timedelta(days=random.randint(1, 30)),
                                config.end_date,
                            ),
                            "returned_quantity": random.randint(1, quantity),
                            "reason": random.choice(
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
    calendar_events = _build_calendar_events(config.start_date, config.end_date)

    tables = {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "returns": returns,
        "promotions": promotions,
        "calendar_events": calendar_events,
    }
    truth = TruthMetadata(
        seed=config.seed,
        start_date=config.start_date,
        end_date=config.end_date,
        row_counts={name: len(table) for name, table in tables.items()},
        issue_counts={name: 0 for name in config.error_rates},
        pattern_parameters={
            "orders_per_customer_year": 1,
            "items_per_order": (1, 3),
            "return_probability": 0.08,
        },
    )

    return GeneratedDataset(**tables, truth=truth)


def _build_calendar_events(start_date: date, end_date: date) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for event_date in calendar_dates(start_date, end_date):
        in_campaign = (
            date(event_date.year, 11, 15) <= event_date <= date(event_date.year, 12, 15)
        )
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
