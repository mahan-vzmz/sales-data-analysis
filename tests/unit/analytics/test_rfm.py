from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from sales_analytics.analytics.rfm import build_rfm

ANALYSIS_DATE = date(2025, 1, 21)


@pytest.fixture
def customers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["A", "B", "C", "D", "E", "returned", "inactive"],
            "last_purchase_date": [
                date(2025, 1, 20),
                date(2025, 1, 20),
                date(2025, 1, 16),
                date(2025, 1, 11),
                date(2025, 1, 1),
                None,
                None,
            ],
            "completed_order_count": [5, 5, 2, 1, 2, 0, 0],
            "order_count": [6, 5, 2, 1, 2, 2, 0],
            "return_adjusted_value": [500, 500, 200, 100, 50, 0, 0],
            "net_sales": [550, 500, 200, 100, 50, 150, 0],
        }
    )


def test_build_rfm_scores_completed_purchases_and_keeps_ties(customers: pd.DataFrame):
    result = build_rfm(customers, ANALYSIS_DATE).set_index("customer_id")

    assert result.loc[
        "D", ["recency_days", "frequency_orders", "monetary_value"]
    ].tolist() == [
        10,
        1,
        100,
    ]
    assert result.loc["A", ["frequency_orders", "monetary_value"]].tolist() == [5, 500]
    scores = ["r_score", "f_score", "m_score", "segment"]
    assert result.loc["A", scores].tolist() == [4, 4, 4, "Champions"]
    assert result.loc["B", scores].tolist() == [4, 4, 4, "Champions"]
    assert result.loc["C", scores].tolist() == [3, 2, 3, "Active"]
    assert result.loc["E", scores].tolist() == [1, 2, 1, "At risk"]
    for customer_id in ("returned", "inactive"):
        assert pd.isna(result.at[customer_id, "recency_days"])
        assert result.loc[customer_id, scores].tolist() == [
            0,
            0,
            0,
            "No completed purchases",
        ]
    reordered = build_rfm(customers.iloc[::-1], ANALYSIS_DATE).set_index("customer_id")
    assert_frame_equal(result.sort_index(), reordered.sort_index())


def test_build_rfm_single_buyer_has_neutral_scores_and_keeps_money_exact(
    customers: pd.DataFrame,
):
    single = customers.iloc[[3]].assign(return_adjusted_value=Decimal("19.99"))
    result = build_rfm(single, date(2025, 1, 11)).iloc[0]

    assert result["recency_days"] == 0
    assert result["monetary_value"] == Decimal("19.99")
    assert result[["r_score", "f_score", "m_score", "segment"]].tolist() == [
        3,
        3,
        3,
        "Active",
    ]


def test_build_rfm_rejects_analysis_date_before_latest_purchase(
    customers: pd.DataFrame,
):
    with pytest.raises(ValueError, match="analysis_date"):
        build_rfm(customers, date(2025, 1, 19))


def test_build_rfm_accepts_empty_snapshot(customers: pd.DataFrame):
    result = build_rfm(customers.iloc[:0], ANALYSIS_DATE)

    assert result.empty
    assert list(result) == [
        "customer_id",
        "recency_days",
        "frequency_orders",
        "monetary_value",
        "r_score",
        "f_score",
        "m_score",
        "segment",
    ]


def test_build_rfm_scores_customer_rows_with_repeated_dataframe_labels(
    customers: pd.DataFrame,
):
    repeated_labels = customers.set_axis([0] * len(customers))

    actual = build_rfm(repeated_labels, ANALYSIS_DATE).reset_index(drop=True)
    expected = build_rfm(customers, ANALYSIS_DATE)

    assert_frame_equal(actual, expected)
