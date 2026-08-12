from collections.abc import Mapping

import pandas as pd
import pytest

from sales_analytics.legacy_pipeline import add_calculated_columns, analyze_sales


@pytest.fixture(scope="session")
def v1_analysis(
    clean_v1_df: pd.DataFrame,
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, pd.DataFrame]:
    persisted_path = tmp_path_factory.mktemp("v1-analysis") / "cleaned.xlsx"
    clean_v1_df.to_excel(persisted_path, sheet_name="Cleaned_Data", index=False)
    persisted = pd.read_excel(persisted_path, sheet_name="Cleaned_Data")
    persisted["Order_Date"] = pd.to_datetime(persisted["Order_Date"])
    return analyze_sales(add_calculated_columns(persisted))


def test_raw_dataset_baseline(raw_v1_df: pd.DataFrame) -> None:
    assert raw_v1_df.shape == (1295, 11)
    assert raw_v1_df["Order_ID"].nunique() == 800


def test_cleaning_output_and_audit_log(
    clean_v1_df: pd.DataFrame,
    cleaning_log_v1: pd.DataFrame,
) -> None:
    assert len(clean_v1_df) == 1275
    assert clean_v1_df["Order_ID"].nunique() == 797
    assert len(cleaning_log_v1) == 8
    assert int(clean_v1_df.duplicated().sum()) == 0
    assert int(clean_v1_df.isna().sum().sum()) == 0

    affected = dict(
        zip(
            cleaning_log_v1["Step"],
            cleaning_log_v1["Rows_Affected"],
            strict=True,
        )
    )
    assert affected["Remove exact duplicates"] == 8
    assert affected["Validate quantity"] == 6
    assert affected["Validate discount rates"] == 5
    assert affected["Validate order dates"] == 5


def test_financial_kpis(v1_analysis: Mapping[str, pd.DataFrame]) -> None:
    summary = v1_analysis["Summary"].set_index("Metric")["Value"]
    expected = {
        "Total Gross Sales (USD)": 453359.22,
        "Total Discount (USD)": 23867.05,
        "Total Net Revenue (USD)": 429492.17,
        "Average Order Value (USD)": 538.89,
        "Average Selling Price (USD)": 158.89,
        "Effective Discount Rate (%)": 5.26,
    }
    for metric, value in expected.items():
        assert float(summary[metric]) == pytest.approx(value)

    assert int(summary["Total Orders"]) == 797
    assert int(summary["Total Units Sold"]) == 2703


def test_rankings(v1_analysis: Mapping[str, pd.DataFrame]) -> None:
    summary = v1_analysis["Summary"].set_index("Metric")["Value"]
    expected = {
        "Top-Selling Product": "Desk Lamp",
        "Highest-Revenue Product": "Laptop",
        "Highest-Revenue Category": "Computers",
        "Highest-Revenue City": "San Francisco",
        "Best Revenue Month": "2025-08",
        "Most-Used Payment Method": "Bank Transfer",
    }
    for metric, value in expected.items():
        assert summary[metric] == value


def test_all_analysis_tables_reconcile_to_total_revenue(
    v1_analysis: Mapping[str, pd.DataFrame],
) -> None:
    summary = v1_analysis["Summary"].set_index("Metric")["Value"]
    total_revenue = float(summary["Total Net Revenue (USD)"])
    table_names = [
        "Monthly_Sales",
        "Product_Analysis",
        "Category_Analysis",
        "City_Analysis",
        "Payment_Analysis",
    ]
    for table_name in table_names:
        table_total = float(v1_analysis[table_name]["Net_Revenue_USD"].sum())
        assert table_total == pytest.approx(total_revenue, abs=0.01)

    assert len(v1_analysis["Monthly_Sales"]) == 12
