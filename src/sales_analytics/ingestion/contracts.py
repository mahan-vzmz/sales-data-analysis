"""Pandera contracts for normalized retail source tables."""

from __future__ import annotations

from datetime import date
from typing import TypeAlias

import pandas as pd
import pandera.pandas as pa
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from sales_analytics.generation.generator import GeneratedDataset

SourceDataset: TypeAlias = GeneratedDataset


def build_source_schemas(
    dataset: SourceDataset,
) -> dict[str, pa.DataFrameSchema]:
    """Build source schemas including relationships for one generated batch."""
    customer_ids = _column_values(dataset.customers, "customer_id")
    product_ids = _column_values(dataset.products, "product_id")
    order_ids = _column_values(dataset.orders, "order_id")
    line_ids = _column_values(dataset.order_items, "line_id")
    promotion_ids = _column_values(dataset.promotions, "promotion_id")
    ordered_quantity = _indexed_reference(
        dataset.order_items, "line_id", "quantity", numeric=True
    )
    line_to_order = _indexed_reference(dataset.order_items, "line_id", "order_id")
    order_dates = _indexed_reference(
        dataset.orders, "order_id", "order_timestamp", datetime=True
    )
    order_date_by_line = (
        None
        if line_to_order is None or order_dates is None
        else line_to_order.map(order_dates.dt.date)
    )

    date_check = pa.Check(
        lambda series: series.map(lambda value: isinstance(value, date)),
        name="date_type",
    )

    return {
        "customers": pa.DataFrameSchema(
            {
                "customer_id": pa.Column(str, unique=True),
                "signup_date": pa.Column(
                    object,
                    [
                        date_check,
                        pa.Check(
                            lambda series: _dates_at_most(
                                series, dataset.truth.end_date
                            ),
                            name="signup_date_on_or_before_batch_end",
                        ),
                    ],
                ),
                "home_city": pa.Column(str),
                "segment": pa.Column(
                    str,
                    pa.Check.isin(
                        ("Consumer", "Corporate", "Small Business"),
                        name="segment_allowed",
                    ),
                ),
            },
            strict=True,
            name="customers",
        ),
        "products": pa.DataFrameSchema(
            {
                "product_id": pa.Column(str, unique=True),
                "name": pa.Column(str),
                "category": pa.Column(str),
                "base_price": pa.Column(
                    float, pa.Check.gt(0, name="base_price_positive")
                ),
                "base_cost": pa.Column(
                    float,
                    pa.Check.gt(0, name="base_cost_positive"),
                ),
            },
            checks=pa.Check(
                lambda frame: _columns_lte(frame, "base_cost", "base_price"),
                name="base_cost_lte_price",
            ),
            strict=True,
            name="products",
        ),
        "orders": pa.DataFrameSchema(
            {
                "order_id": pa.Column(str, unique=True),
                "customer_id": pa.Column(
                    str,
                    _foreign_key_check(customer_ids, "customer_id_foreign_key"),
                ),
                "order_timestamp": pa.Column(
                    pa.DateTime,
                    pa.Check(
                        lambda series: _timestamps_in_range(
                            series, dataset.truth.start_date, dataset.truth.end_date
                        ),
                        name="order_timestamp_in_range",
                    ),
                ),
                "channel": pa.Column(
                    str,
                    pa.Check.isin(
                        ("Online", "Store", "Marketplace"),
                        name="channel_allowed",
                    ),
                ),
                "payment_method": pa.Column(
                    str,
                    pa.Check.isin(
                        ("Credit Card", "Debit Card", "Digital Wallet"),
                        name="payment_method_allowed",
                    ),
                ),
                "promotion_id": pa.Column(
                    str,
                    _foreign_key_check(promotion_ids, "promotion_id_foreign_key"),
                    nullable=True,
                ),
            },
            strict=True,
            name="orders",
        ),
        "order_items": pa.DataFrameSchema(
            {
                "line_id": pa.Column(str, unique=True),
                "order_id": pa.Column(
                    str, _foreign_key_check(order_ids, "order_id_foreign_key")
                ),
                "product_id": pa.Column(
                    str,
                    _foreign_key_check(product_ids, "product_id_foreign_key"),
                ),
                "quantity": pa.Column(int, pa.Check.gt(0, name="quantity_positive")),
                "unit_price": pa.Column(
                    float, pa.Check.gt(0, name="unit_price_positive")
                ),
                "unit_cost": pa.Column(
                    float, pa.Check.gt(0, name="unit_cost_positive")
                ),
                "discount_rate": pa.Column(
                    float,
                    pa.Check.in_range(0, 1, name="discount_rate_between_zero_and_one"),
                ),
            },
            checks=pa.Check(
                lambda frame: _columns_lte(frame, "unit_cost", "unit_price"),
                name="unit_cost_lte_unit_price",
            ),
            strict=True,
            name="order_items",
        ),
        "returns": pa.DataFrameSchema(
            {
                "return_id": pa.Column(str, unique=True),
                "line_id": pa.Column(
                    str, _foreign_key_check(line_ids, "line_id_foreign_key")
                ),
                "return_date": pa.Column(
                    object,
                    [
                        date_check,
                        pa.Check(
                            lambda series: _dates_at_most(
                                series, dataset.truth.end_date
                            ),
                            name="return_date_on_or_before_batch_end",
                        ),
                    ],
                ),
                "returned_quantity": pa.Column(
                    int,
                    pa.Check.gt(0, name="returned_quantity_positive"),
                ),
                "reason": pa.Column(
                    str,
                    pa.Check.isin(
                        ("Damaged", "Changed mind", "Wrong item"),
                        name="return_reason_allowed",
                    ),
                ),
            },
            checks=[
                pa.Check(
                    lambda frame: _column_lte_reference(
                        frame, "returned_quantity", "line_id", ordered_quantity
                    ),
                    name="returned_quantity_lte_ordered",
                ),
                pa.Check(
                    lambda frame: _column_gte_reference(
                        frame, "return_date", "line_id", order_date_by_line
                    ),
                    name="return_date_on_or_after_order",
                ),
            ],
            strict=True,
            name="returns",
        ),
        "promotions": pa.DataFrameSchema(
            {
                "promotion_id": pa.Column(str, unique=True),
                "promotion_type": pa.Column(str),
                "start_date": pa.Column(
                    object,
                    [
                        date_check,
                        pa.Check(
                            lambda series: _dates_in_range(
                                series, dataset.truth.start_date, dataset.truth.end_date
                            ),
                            name="promotion_start_date_in_range",
                        ),
                    ],
                ),
                "end_date": pa.Column(
                    object,
                    [
                        date_check,
                        pa.Check(
                            lambda series: _dates_in_range(
                                series, dataset.truth.start_date, dataset.truth.end_date
                            ),
                            name="promotion_end_date_in_range",
                        ),
                    ],
                ),
                "discount_policy": pa.Column(
                    float,
                    pa.Check.in_range(
                        0, 1, name="discount_policy_between_zero_and_one"
                    ),
                ),
            },
            checks=pa.Check(
                lambda frame: _columns_lte(frame, "start_date", "end_date"),
                name="promotion_start_lte_end",
            ),
            strict=True,
            name="promotions",
        ),
        "calendar_events": pa.DataFrameSchema(
            {
                "date": pa.Column(
                    object,
                    [
                        date_check,
                        pa.Check(
                            lambda series: _dates_in_range(
                                series, dataset.truth.start_date, dataset.truth.end_date
                            ),
                            name="calendar_date_in_range",
                        ),
                    ],
                    unique=True,
                ),
                "holiday": pa.Column(str, nullable=True),
                "campaign": pa.Column(str, nullable=True),
                "seasonal_event": pa.Column(
                    str,
                    pa.Check.isin(
                        ("Winter", "Spring", "Summer", "Autumn"),
                        name="season_allowed",
                    ),
                ),
            },
            strict=True,
            name="calendar_events",
        ),
    }


def _column_values(frame: pd.DataFrame, column: str) -> set[object] | None:
    if column not in frame:
        return None
    return set(frame[column].dropna())


def _indexed_reference(
    frame: pd.DataFrame,
    key: str,
    value: str,
    *,
    numeric: bool = False,
    datetime: bool = False,
) -> pd.Series | None:
    if key not in frame or value not in frame or frame[key].duplicated().any():
        return None
    values = frame[value]
    if numeric and not is_numeric_dtype(values.dtype):
        return None
    if datetime and not is_datetime64_any_dtype(values.dtype):
        return None
    return frame.set_index(key)[value]


def _foreign_key_check(allowed_values: set[object] | None, name: str) -> pa.Check:
    if allowed_values is None:
        return pa.Check(lambda _series: True, name=name)
    return pa.Check.isin(allowed_values, name=name)


def _dates_at_most(series: pd.Series, maximum: date) -> pd.Series:
    return series.map(lambda value: isinstance(value, date) and value <= maximum)


def _dates_in_range(series: pd.Series, minimum: date, maximum: date) -> pd.Series:
    return series.map(
        lambda value: isinstance(value, date) and minimum <= value <= maximum
    )


def _timestamps_in_range(series: pd.Series, minimum: date, maximum: date) -> pd.Series:
    return series.map(
        lambda value: (
            isinstance(value, pd.Timestamp) and minimum <= value.date() <= maximum
        )
    )


def _columns_lte(frame: pd.DataFrame, left: str, right: str) -> pd.Series:
    if left not in frame or right not in frame:
        return pd.Series(True, index=frame.index)
    try:
        return frame[left] <= frame[right]
    except TypeError:
        return pd.Series(True, index=frame.index)


def _column_lte_reference(
    frame: pd.DataFrame,
    value_column: str,
    key_column: str,
    reference: pd.Series | None,
) -> pd.Series:
    if reference is None or value_column not in frame or key_column not in frame:
        return pd.Series(True, index=frame.index)
    try:
        return frame[value_column] <= frame[key_column].map(reference)
    except TypeError:
        return pd.Series(True, index=frame.index)


def _column_gte_reference(
    frame: pd.DataFrame,
    value_column: str,
    key_column: str,
    reference: pd.Series | None,
) -> pd.Series:
    if reference is None or value_column not in frame or key_column not in frame:
        return pd.Series(True, index=frame.index)
    try:
        return frame[value_column] >= frame[key_column].map(reference)
    except TypeError:
        return pd.Series(True, index=frame.index)
