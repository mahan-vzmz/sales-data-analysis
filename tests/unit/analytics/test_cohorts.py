import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from sales_analytics.analytics.cohorts import build_retention_matrix


@pytest.fixture
def purchases() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("A", "2024-12-01", "2024-12-01", 1),
            ("B", "2024-12-01", "2024-12-01", 2),
            ("A", "2025-01-01", "2024-12-01", 1),
            ("A", "2025-01-01", "2024-12-01", 3),
            ("C", "2025-02-01", "2025-02-01", 1),
            ("B", "2025-03-01", "2024-12-01", 1),
            ("B", "2024-11-01", None, 0),
            ("C", "2025-03-01", None, 0),
            ("D", "2025-04-01", None, 0),
        ],
        columns=[
            "customer_id",
            "order_month",
            "acquisition_cohort_month",
            "retained_quantity",
        ],
    )


def test_retention_counts_distinct_buyers_with_a_fixed_cohort_denominator(
    purchases: pd.DataFrame,
) -> None:
    result = build_retention_matrix(purchases)
    december, february = pd.to_datetime(["2024-12-01", "2025-02-01"])
    rows = list(result.long_form.itertuples(index=False, name=None))

    assert rows == [
        (december, 0, 2, 2, 1.0),
        (december, 1, 2, 1, 0.5),
        (december, 2, 2, 0, 0.0),
        (december, 3, 2, 1, 0.5),
        (february, 0, 1, 1, 1.0),
        (february, 1, 1, 0, 0.0),
    ]
    assert list(result.matrix.index) == [december, february]
    assert list(result.matrix.columns) == [0, 1, 2, 3]
    assert result.matrix.loc[december].tolist() == [1.0, 0.5, 0.0, 0.5]
    assert result.matrix.loc[february, 1] == 0.0
    assert pd.isna(result.matrix.loc[february, 2])


def test_month_zero_population_reconciles_to_eligible_customers(
    purchases: pd.DataFrame,
) -> None:
    before = purchases.copy(deep=True)
    result = build_retention_matrix(purchases)
    month_zero = result.long_form.query("cohort_age == 0")

    assert month_zero["cohort_size"].sum() == 3
    assert (
        month_zero["cohort_size"].sum()
        == purchases.loc[purchases["retained_quantity"] > 0, "customer_id"].nunique()
    )
    reordered = build_retention_matrix(purchases.iloc[::-1])
    assert_frame_equal(result.long_form, reordered.long_form)
    assert_frame_equal(purchases, before)


def test_fully_returned_only_snapshot_has_empty_outputs(
    purchases: pd.DataFrame,
) -> None:
    result = build_retention_matrix(purchases.tail(3))

    assert result.matrix.empty
    assert result.long_form.empty
    assert list(result.long_form) == [
        "cohort_month",
        "cohort_age",
        "cohort_size",
        "active_customers",
        "retention_rate",
    ]


def test_missing_acquisition_purchase_is_rejected(purchases: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="first completed purchase"):
        build_retention_matrix(purchases.iloc[1:])
