"""Compatibility entry point for the packaged v1 sales pipeline."""

from pathlib import Path

from sales_analytics.config import Settings
from sales_analytics.legacy_pipeline import run_legacy_pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
