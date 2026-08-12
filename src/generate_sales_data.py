from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RANDOM_SEED = 42
NUMBER_OF_ORDERS = 800

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "sales_data.xlsx"

PRODUCT_CATALOG = [
    ("Laptop", "Computers", 950.00),
    ("Monitor", "Computers", 280.00),
    ("Keyboard", "Accessories", 75.00),
    ("Wireless Mouse", "Accessories", 45.00),
    ("USB-C Hub", "Accessories", 65.00),
    ("Webcam", "Accessories", 90.00),
    ("Headphones", "Audio", 130.00),
    ("Bluetooth Speaker", "Audio", 110.00),
    ("External SSD", "Storage", 150.00),
    ("USB Flash Drive", "Storage", 30.00),
    ("Office Chair", "Furniture", 240.00),
    ("Desk Lamp", "Furniture", 55.00),
]

CITIES = [
    "New York",
    "Chicago",
    "Austin",
    "Seattle",
    "Boston",
    "San Francisco",
]

PAYMENT_METHODS = [
    "Credit Card",
    "Debit Card",
    "PayPal",
    "Bank Transfer",
]

DISCOUNT_RATES = [0.00, 0.05, 0.10, 0.15, 0.20]


def build_clean_order_lines() -> pd.DataFrame:
    """Create valid sales order lines before injecting data-quality issues."""

    rng = random.Random(RANDOM_SEED)
    rows: list[dict[str, object]] = []
    line_number = 1
    first_day = date(2025, 1, 1)

    for order_number in range(1, NUMBER_OF_ORDERS + 1):
        order_id = f"ORD-2025-{order_number:04d}"
        order_date = first_day + timedelta(days=rng.randrange(365))
        customer_id = f"CUS-{rng.randint(1, 350):04d}"
        city = rng.choice(CITIES)
        payment_method = rng.choice(PAYMENT_METHODS)

        line_count = rng.choices(
            [1, 2, 3],
            weights=[50, 35, 15],
            k=1,
        )[0]

        selected_products = rng.sample(
            PRODUCT_CATALOG,
            line_count,
        )

        for product, category, base_price in selected_products:
            quantity = rng.choices(
                [1, 2, 3, 4, 5],
                weights=[40, 28, 18, 9, 5],
                k=1,
            )[0]

            unit_price = round(
                base_price * rng.uniform(0.92, 1.08),
                2,
            )

            discount_rate = rng.choices(
                DISCOUNT_RATES,
                weights=[45, 25, 17, 9, 4],
                k=1,
            )[0]

            rows.append(
                {
                    "Order_Line_ID": f"LINE-{line_number:05d}",
                    "Order_ID": order_id,
                    "Order_Date": order_date,
                    "Customer_ID": customer_id,
                    "Product": product,
                    "Category": category,
                    "City": city,
                    "Quantity": quantity,
                    "Unit_Price_USD": unit_price,
                    "Discount_Rate": discount_rate,
                    "Payment_Method": payment_method,
                }
            )

            line_number += 1

    return pd.DataFrame(rows)


def inject_data_quality_issues(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Add controlled problems to an otherwise valid dataset."""

    dirty = df.copy()

    # Quantity must accept both numbers and intentionally invalid text.
    dirty["Quantity"] = dirty["Quantity"].astype("object")

    rng = random.Random(RANDOM_SEED + 1)
    available_indices = list(dirty.index)
    rng.shuffle(available_indices)

    cursor = 0
    issue_counts: dict[str, int] = {}

    def take_indices(
        issue_name: str,
        count: int,
    ) -> list[int]:
        nonlocal cursor

        selected = available_indices[cursor : cursor + count]
        cursor += count
        issue_counts[issue_name] = count

        return selected

    missing_city_indices = take_indices("missing_city", 10)
    dirty.loc[missing_city_indices, "City"] = None

    missing_payment_indices = take_indices(
        "missing_payment_method",
        8,
    )
    dirty.loc[
        missing_payment_indices,
        "Payment_Method",
    ] = None

    for index in take_indices("city_extra_spaces", 8):
        city = dirty.at[index, "City"]
        dirty.at[index, "City"] = f"  {city} "

    for position, index in enumerate(take_indices("city_wrong_case", 8)):
        city = str(dirty.at[index, "City"])

        if position % 2 == 0:
            dirty.at[index, "City"] = city.lower()
        else:
            dirty.at[index, "City"] = city.upper()

    invalid_quantities: list[object] = [
        0,
        -1,
        "three",
        0,
        -2,
        "unknown",
    ]

    for index, value in zip(
        take_indices("invalid_quantity", 6),
        invalid_quantities,
    ):
        dirty.at[index, "Quantity"] = value

    invalid_prices = [
        0,
        -25.0,
        0,
        -100.0,
        0,
    ]

    for index, value in zip(
        take_indices("invalid_unit_price", 5),
        invalid_prices,
    ):
        dirty.at[index, "Unit_Price_USD"] = value

    invalid_discounts = [
        -0.10,
        1.20,
        -0.05,
        1.50,
        2.00,
    ]

    for index, value in zip(
        take_indices("invalid_discount_rate", 5),
        invalid_discounts,
    ):
        dirty.at[index, "Discount_Rate"] = value

    invalid_dates = [
        "not-a-date",
        "2025-13-40",
        "unknown",
        "31/31/2025",
        "2024-12-31",
    ]

    for index, value in zip(
        take_indices("invalid_order_date", 5),
        invalid_dates,
    ):
        dirty.at[index, "Order_Date"] = value

    wrong_categories = [
        "Audio",
        "Furniture",
        "Storage",
        "Computers",
        "Accessories",
    ]

    for index, value in zip(
        take_indices("product_category_mismatch", 5),
        wrong_categories,
    ):
        current_category = dirty.at[index, "Category"]

        if value != current_category:
            dirty.at[index, "Category"] = value
        else:
            dirty.at[index, "Category"] = "Unknown"

    duplicate_source_indices = available_indices[cursor : cursor + 8]

    duplicate_rows = dirty.loc[duplicate_source_indices].copy()

    dirty = pd.concat(
        [dirty, duplicate_rows],
        ignore_index=True,
    )

    issue_counts["exact_duplicate_rows"] = len(duplicate_rows)

    return dirty, issue_counts


def main() -> None:
    """Generate and export the raw sales dataset."""

    clean_data = build_clean_order_lines()

    raw_data, issue_counts = inject_data_quality_issues(clean_data)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_data.to_excel(
        OUTPUT_PATH,
        index=False,
        sheet_name="Raw_Sales_Data",
    )

    print("Sales dataset created successfully.")
    print("Output:", OUTPUT_PATH)
    print("Clean base rows:", len(clean_data))
    print(
        "Raw rows including duplicates:",
        len(raw_data),
    )
    print(
        "Unique orders:",
        raw_data["Order_ID"].nunique(),
    )

    print("Planned data-quality issues:")

    for issue_name, count in issue_counts.items():
        print(f"  - {issue_name}: {count}")


if __name__ == "__main__":
    main()
