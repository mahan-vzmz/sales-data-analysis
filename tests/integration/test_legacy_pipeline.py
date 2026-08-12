from pathlib import Path
from shutil import copy2

import pandas as pd
import pytest

from sales_analytics.config import Settings
from sales_analytics.legacy_pipeline import run_legacy_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_legacy_pipeline_preserves_v1_results(tmp_path: Path) -> None:
    raw_path = tmp_path / "data" / "raw" / "sales_data.xlsx"
    raw_path.parent.mkdir(parents=True)
    copy2(PROJECT_ROOT / "data" / "raw" / "sales_data.xlsx", raw_path)
    raw_before = raw_path.read_bytes()

    result = run_legacy_pipeline(Settings.from_root(tmp_path))

    assert result.raw_rows == 1295
    assert result.clean_rows == 1275
    assert result.unique_orders == 797
    assert result.units_sold == 2703
    assert result.gross_sales == pytest.approx(453359.22)
    assert result.net_revenue == pytest.approx(429492.17)
    assert result.cleaned_workbook_path == (
        tmp_path / "data" / "processed" / "cleaned_sales_data.xlsx"
    )
    assert result.report_path == tmp_path / "reports" / "sales_report.xlsx"
    assert result.cleaned_workbook_path.exists()
    assert result.report_path.exists()
    assert raw_path.read_bytes() == raw_before

    summary = pd.read_excel(
        result.report_path,
        sheet_name="Summary",
    ).set_index("Metric")["Value"]
    expected_kpis = {
        "Total Gross Sales (USD)": 453359.22,
        "Total Discount (USD)": 23867.05,
        "Total Net Revenue (USD)": 429492.17,
        "Total Orders": 797,
        "Total Units Sold": 2703,
        "Average Order Value (USD)": 538.89,
        "Average Selling Price (USD)": 158.89,
        "Effective Discount Rate (%)": 5.26,
        "Top-Selling Product": "Desk Lamp",
        "Highest-Revenue Product": "Laptop",
        "Highest-Revenue Category": "Computers",
        "Highest-Revenue City": "San Francisco",
        "Best Revenue Month": "2025-08",
        "Most-Used Payment Method": "Bank Transfer",
    }
    for metric, expected in expected_kpis.items():
        assert summary[metric] == expected

    for sheet_name in [
        "Monthly_Sales",
        "Product_Analysis",
        "Category_Analysis",
        "City_Analysis",
        "Payment_Analysis",
    ]:
        table = pd.read_excel(result.report_path, sheet_name=sheet_name)
        assert table["Net_Revenue_USD"].sum() == pytest.approx(
            429492.17,
            abs=0.01,
        )
