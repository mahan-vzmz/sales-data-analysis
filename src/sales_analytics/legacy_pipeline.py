"""Packaged implementation of the unchanged v1 Pandas/Excel pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sales_analytics.config import Settings
from sales_analytics.exports.excel import (
    export_cleaned_workbook,
    export_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sales_data.xlsx"

PRODUCT_CATEGORY_MAP = {
    "Laptop": "Computers",
    "Monitor": "Computers",
    "Keyboard": "Accessories",
    "Wireless Mouse": "Accessories",
    "USB-C Hub": "Accessories",
    "Webcam": "Accessories",
    "Headphones": "Audio",
    "Bluetooth Speaker": "Audio",
    "External SSD": "Storage",
    "USB Flash Drive": "Storage",
    "Office Chair": "Furniture",
    "Desk Lamp": "Furniture",
}

PAYMENT_METHOD_MAP = {
    "credit card": "Credit Card",
    "debit card": "Debit Card",
    "paypal": "PayPal",
    "bank transfer": "Bank Transfer",
}


@dataclass(frozen=True)
class PipelineResult:
    """Stable outputs and headline metrics from one pipeline run."""

    raw_rows: int
    clean_rows: int
    unique_orders: int
    units_sold: int
    gross_sales: float
    net_revenue: float
    cleaned_workbook_path: Path
    report_path: Path


def load_raw_data(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Load the original order-line dataset without modifying it."""

    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset was not found: {path}\nRun src/generate_sales_data.py first."
        )

    return pd.read_excel(path, sheet_name="Raw_Sales_Data")


def _recover_order_level_values(
    data: pd.DataFrame,
    column: str,
) -> tuple[pd.Series, int, int]:
    """Recover missing order-level values from another line of the same order."""

    missing_before = int(data[column].isna().sum())
    recovered_series = data.groupby("Order_ID")[column].transform(
        lambda values: values.ffill().bfill()
    )
    missing_after = int(recovered_series.isna().sum())
    recovered_count = missing_before - missing_after

    return recovered_series.fillna("Unknown"), recovered_count, missing_after


def clean_data(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean raw sales data and return the cleaned rows plus an audit log."""

    data = raw_df.copy()
    log: list[dict[str, object]] = []

    duplicate_count = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()
    log.append(
        {
            "Step": "Remove exact duplicates",
            "Rows_Affected": duplicate_count,
            "Decision": "Removed completely identical rows",
        }
    )

    for column in ["Product", "Category", "City", "Payment_Method"]:
        data[column] = data[column].astype("string").str.strip()

    data["City"] = data["City"].str.title()
    data["Payment_Method"] = (
        data["Payment_Method"].str.casefold().map(PAYMENT_METHOD_MAP).astype("string")
    )

    for column in ["City", "Payment_Method"]:
        missing_before = int(data[column].isna().sum())
        recovered, recovered_count, unknown_count = _recover_order_level_values(
            data,
            column,
        )
        data[column] = recovered
        log.append(
            {
                "Step": f"Handle missing {column}",
                "Rows_Affected": missing_before,
                "Decision": (
                    f"Recovered {recovered_count} from the same order; "
                    f"labeled {unknown_count} as Unknown"
                ),
            }
        )

    numeric_quantity = pd.to_numeric(data["Quantity"], errors="coerce")
    invalid_quantity = numeric_quantity.isna() | (numeric_quantity <= 0)
    invalid_quantity_count = int(invalid_quantity.sum())
    data = data.loc[~invalid_quantity].copy()
    data["Quantity"] = numeric_quantity.loc[~invalid_quantity].astype("int64")
    log.append(
        {
            "Step": "Validate quantity",
            "Rows_Affected": invalid_quantity_count,
            "Decision": "Removed rows with non-numeric, zero, or negative quantity",
        }
    )

    invalid_price = data["Unit_Price_USD"] <= 0
    invalid_price_count = int(invalid_price.sum())
    product_medians = (
        data.loc[~invalid_price].groupby("Product")["Unit_Price_USD"].median()
    )
    data.loc[invalid_price, "Unit_Price_USD"] = data.loc[invalid_price, "Product"].map(
        product_medians
    )
    log.append(
        {
            "Step": "Repair unit prices",
            "Rows_Affected": invalid_price_count,
            "Decision": "Replaced with median valid price for the same product",
        }
    )

    invalid_discount = ~data["Discount_Rate"].between(0, 1)
    invalid_discount_count = int(invalid_discount.sum())
    data = data.loc[~invalid_discount].copy()
    log.append(
        {
            "Step": "Validate discount rates",
            "Rows_Affected": invalid_discount_count,
            "Decision": "Removed rows with discount rates outside 0-1",
        }
    )

    parsed_dates = pd.to_datetime(data["Order_Date"], errors="coerce")
    invalid_date = parsed_dates.isna() | (parsed_dates.dt.year != 2025)
    invalid_date_count = int(invalid_date.sum())
    data["Order_Date"] = parsed_dates.mask(invalid_date)
    data["Order_Date"] = data.groupby("Order_ID")["Order_Date"].transform(
        lambda values: values.ffill().bfill()
    )
    unrecoverable_dates = int(data["Order_Date"].isna().sum())
    data = data.dropna(subset=["Order_Date"]).copy()
    log.append(
        {
            "Step": "Validate order dates",
            "Rows_Affected": invalid_date_count,
            "Decision": (
                f"Recovered {invalid_date_count - unrecoverable_dates} from the "
                f"same order; removed {unrecoverable_dates} unrecoverable rows"
            ),
        }
    )

    expected_category = data["Product"].map(PRODUCT_CATEGORY_MAP)
    mismatch_count = int((data["Category"] != expected_category).sum())
    data["Category"] = expected_category
    log.append(
        {
            "Step": "Correct product categories",
            "Rows_Affected": mismatch_count,
            "Decision": "Replaced with the approved category for each product",
        }
    )

    data = data.reset_index(drop=True)
    validate_clean_data(data)

    return data, pd.DataFrame(log)


def validate_clean_data(data: pd.DataFrame) -> None:
    """Raise an AssertionError if a required data-quality rule is violated."""

    assert data.duplicated().sum() == 0, "Exact duplicates remain"
    assert data["Order_Line_ID"].duplicated().sum() == 0, "Line IDs are duplicated"
    assert data.isna().sum().sum() == 0, "Missing values remain"
    assert (data["Quantity"] > 0).all(), "Invalid quantities remain"
    assert (data["Unit_Price_USD"] > 0).all(), "Invalid prices remain"
    assert data["Discount_Rate"].between(0, 1).all(), "Invalid discounts remain"
    assert (data["Order_Date"].dt.year == 2025).all(), "Invalid dates remain"
    assert data["Category"].eq(data["Product"].map(PRODUCT_CATEGORY_MAP)).all(), (
        "Product/category mismatches remain"
    )


def add_calculated_columns(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Create auditable financial and time-analysis columns."""

    data = clean_df.copy()
    data["Gross_Sales_USD"] = (data["Quantity"] * data["Unit_Price_USD"]).round(2)
    data["Discount_Amount_USD"] = (
        data["Gross_Sales_USD"] * data["Discount_Rate"]
    ).round(2)
    data["Net_Revenue_USD"] = (
        data["Gross_Sales_USD"] - data["Discount_Amount_USD"]
    ).round(2)
    data["Year"] = data["Order_Date"].dt.year
    data["Month"] = data["Order_Date"].dt.to_period("M").astype(str)
    data["Month_Name"] = data["Order_Date"].dt.month_name()

    return data


def build_grouped_analysis(
    data: pd.DataFrame,
    group_columns: list[str],
    total_revenue: float,
) -> pd.DataFrame:
    """Create a reusable grouped sales summary."""

    result = data.groupby(group_columns, as_index=False).agg(
        Units_Sold=("Quantity", "sum"),
        Orders=("Order_ID", "nunique"),
        Gross_Sales_USD=("Gross_Sales_USD", "sum"),
        Discount_Amount_USD=("Discount_Amount_USD", "sum"),
        Net_Revenue_USD=("Net_Revenue_USD", "sum"),
    )

    money_columns = [
        "Gross_Sales_USD",
        "Discount_Amount_USD",
        "Net_Revenue_USD",
    ]
    result[money_columns] = result[money_columns].round(2)
    result["Average_Order_Value_USD"] = (
        result["Net_Revenue_USD"] / result["Orders"]
    ).round(2)
    result["Revenue_Share_Pct"] = (
        result["Net_Revenue_USD"] / total_revenue * 100
    ).round(2)

    return result.sort_values(
        "Net_Revenue_USD",
        ascending=False,
    ).reset_index(drop=True)


def analyze_sales(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Calculate KPIs and all final analysis tables."""

    total_gross = float(data["Gross_Sales_USD"].sum())
    total_discount = float(data["Discount_Amount_USD"].sum())
    total_revenue = float(data["Net_Revenue_USD"].sum())
    total_orders = int(data["Order_ID"].nunique())
    total_units = int(data["Quantity"].sum())

    product = build_grouped_analysis(
        data,
        ["Product", "Category"],
        total_revenue,
    )
    category = build_grouped_analysis(data, ["Category"], total_revenue)
    city = build_grouped_analysis(data, ["City"], total_revenue)
    monthly = (
        build_grouped_analysis(data, ["Month"], total_revenue)
        .sort_values("Month")
        .reset_index(drop=True)
    )
    payment = build_grouped_analysis(
        data,
        ["Payment_Method"],
        total_revenue,
    )

    top_selling_product = product.sort_values(
        ["Units_Sold", "Net_Revenue_USD"],
        ascending=[False, False],
    ).iloc[0]
    top_city = city.loc[city["City"] != "Unknown"].iloc[0]
    best_month = monthly.loc[monthly["Net_Revenue_USD"].idxmax()]

    summary = pd.DataFrame(
        [
            ("Total Gross Sales (USD)", round(total_gross, 2)),
            ("Total Discount (USD)", round(total_discount, 2)),
            ("Total Net Revenue (USD)", round(total_revenue, 2)),
            ("Total Orders", total_orders),
            ("Total Units Sold", total_units),
            ("Average Order Value (USD)", round(total_revenue / total_orders, 2)),
            ("Average Selling Price (USD)", round(total_revenue / total_units, 2)),
            (
                "Effective Discount Rate (%)",
                round(total_discount / total_gross * 100, 2),
            ),
            ("Top-Selling Product", top_selling_product["Product"]),
            ("Highest-Revenue Product", product.iloc[0]["Product"]),
            ("Highest-Revenue Category", category.iloc[0]["Category"]),
            ("Highest-Revenue City", top_city["City"]),
            ("Best Revenue Month", best_month["Month"]),
            (
                "Most-Used Payment Method",
                payment.sort_values("Orders", ascending=False).iloc[0][
                    "Payment_Method"
                ],
            ),
        ],
        columns=["Metric", "Value"],
    )

    for table in [product, category, city, monthly, payment]:
        assert abs(float(table["Net_Revenue_USD"].sum()) - total_revenue) <= 0.01

    return {
        "Summary": summary,
        "Monthly_Sales": monthly,
        "Product_Analysis": product,
        "Category_Analysis": category,
        "City_Analysis": city,
        "Payment_Analysis": payment,
    }


def run_legacy_pipeline(settings: Settings) -> PipelineResult:
    """Run the v1 workflow using paths derived from ``settings``."""

    raw_path = settings.project_root / "data" / "raw" / "sales_data.xlsx"
    cleaned_path = (
        settings.project_root / "data" / "processed" / "cleaned_sales_data.xlsx"
    )
    report_path = settings.report_dir / "sales_report.xlsx"

    raw_df = load_raw_data(raw_path)
    clean_df, cleaning_log = clean_data(raw_df)
    export_cleaned_workbook(clean_df, cleaning_log, cleaned_path)

    persisted_clean_df = pd.read_excel(cleaned_path, sheet_name="Cleaned_Data")
    persisted_clean_df["Order_Date"] = pd.to_datetime(persisted_clean_df["Order_Date"])

    analysis_df = add_calculated_columns(persisted_clean_df)
    analyses = analyze_sales(analysis_df)
    export_report(analysis_df, analyses, report_path)

    summary = analyses["Summary"].set_index("Metric")["Value"]
    return PipelineResult(
        raw_rows=len(raw_df),
        clean_rows=len(clean_df),
        unique_orders=int(clean_df["Order_ID"].nunique()),
        units_sold=int(clean_df["Quantity"].sum()),
        gross_sales=float(summary["Total Gross Sales (USD)"]),
        net_revenue=float(summary["Total Net Revenue (USD)"]),
        cleaned_workbook_path=cleaned_path,
        report_path=report_path,
    )
