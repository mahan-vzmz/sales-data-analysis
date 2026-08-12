"""Compatibility entry point for the packaged v1 sales pipeline."""

from pathlib import Path

from sales_analytics.config import Settings
from sales_analytics.legacy_pipeline import (
    PAYMENT_METHOD_MAP,
    PRODUCT_CATEGORY_MAP,
    RAW_DATA_PATH,
    add_calculated_columns,
    analyze_sales,
    build_grouped_analysis,
    clean_data,
    load_raw_data,
    run_legacy_pipeline,
    validate_clean_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "cleaned_sales_data.xlsx"
)
REPORT_PATH = PROJECT_ROOT / "reports" / "sales_report.xlsx"


def main() -> None:
    """Run the packaged pipeline while preserving the v1 console output."""

    result = run_legacy_pipeline(Settings.from_root(PROJECT_ROOT))

    print("Sales analysis completed successfully.")
    print(f"Raw rows: {result.raw_rows:,}")
    print(f"Clean rows: {result.clean_rows:,}")
    print(f"Unique orders: {result.unique_orders:,}")
    print(f"Units sold: {result.units_sold:,}")
    print(f"Net revenue: ${result.net_revenue:,.2f}")
    print(f"Cleaned workbook: {result.cleaned_workbook_path}")
    print(f"Analysis workbook: {result.report_path}")


if __name__ == "__main__":
    main()
