"""Integration tests for the reproducible sales-analysis pipeline.

Run from the project root with:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import src.sales_analysis as sales  # noqa: E402


class SalesAnalysisPipelineTests(unittest.TestCase):
    """Validate cleaning rules, KPIs, rankings, and reconciliations."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = sales.load_raw_data()
        cls.clean, cls.cleaning_log = sales.clean_data(cls.raw)

        # Match the production workflow: Excel is the persisted boundary between
        # cleaning and analysis, so the tests use the same round-trip.
        cls.temp_dir = tempfile.TemporaryDirectory()
        persisted_path = Path(cls.temp_dir.name) / "cleaned_sales_data.xlsx"
        cls.clean.to_excel(
            persisted_path,
            sheet_name="Cleaned_Data",
            index=False,
        )
        persisted = pd.read_excel(persisted_path, sheet_name="Cleaned_Data")
        persisted["Order_Date"] = pd.to_datetime(persisted["Order_Date"])

        cls.analysis_data = sales.add_calculated_columns(persisted)
        cls.analyses = sales.analyze_sales(cls.analysis_data)
        cls.summary = cls.analyses["Summary"].set_index("Metric")["Value"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_raw_dataset_baseline(self) -> None:
        self.assertEqual(self.raw.shape, (1295, 11))
        self.assertEqual(self.raw["Order_ID"].nunique(), 800)

    def test_cleaning_output_and_audit_log(self) -> None:
        self.assertEqual(len(self.clean), 1275)
        self.assertEqual(self.clean["Order_ID"].nunique(), 797)
        self.assertEqual(len(self.cleaning_log), 8)
        self.assertEqual(int(self.clean.duplicated().sum()), 0)
        self.assertEqual(int(self.clean.isna().sum().sum()), 0)

        affected = dict(
            zip(
                self.cleaning_log["Step"],
                self.cleaning_log["Rows_Affected"],
            )
        )
        self.assertEqual(affected["Remove exact duplicates"], 8)
        self.assertEqual(affected["Validate quantity"], 6)
        self.assertEqual(affected["Validate discount rates"], 5)
        self.assertEqual(affected["Validate order dates"], 5)

    def test_financial_kpis(self) -> None:
        expected = {
            "Total Gross Sales (USD)": 453359.22,
            "Total Discount (USD)": 23867.05,
            "Total Net Revenue (USD)": 429492.17,
            "Average Order Value (USD)": 538.89,
            "Average Selling Price (USD)": 158.89,
            "Effective Discount Rate (%)": 5.26,
        }
        for metric, value in expected.items():
            with self.subTest(metric=metric):
                self.assertAlmostEqual(float(self.summary[metric]), value, places=2)

        self.assertEqual(int(self.summary["Total Orders"]), 797)
        self.assertEqual(int(self.summary["Total Units Sold"]), 2703)

    def test_rankings(self) -> None:
        expected = {
            "Top-Selling Product": "Desk Lamp",
            "Highest-Revenue Product": "Laptop",
            "Highest-Revenue Category": "Computers",
            "Highest-Revenue City": "San Francisco",
            "Best Revenue Month": "2025-08",
            "Most-Used Payment Method": "Bank Transfer",
        }
        for metric, value in expected.items():
            with self.subTest(metric=metric):
                self.assertEqual(self.summary[metric], value)

    def test_all_analysis_tables_reconcile_to_total_revenue(self) -> None:
        total_revenue = float(self.summary["Total Net Revenue (USD)"])
        table_names = [
            "Monthly_Sales",
            "Product_Analysis",
            "Category_Analysis",
            "City_Analysis",
            "Payment_Analysis",
        ]
        for table_name in table_names:
            with self.subTest(table=table_name):
                table_total = float(
                    self.analyses[table_name]["Net_Revenue_USD"].sum()
                )
                self.assertAlmostEqual(table_total, total_revenue, places=2)

        self.assertEqual(len(self.analyses["Monthly_Sales"]), 12)


if __name__ == "__main__":
    unittest.main()