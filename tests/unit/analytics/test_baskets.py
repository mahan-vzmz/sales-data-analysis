import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from sales_analytics.analytics.baskets import build_basket_rules


@pytest.fixture
def baskets() -> pd.DataFrame:
    return pd.DataFrame(
        [
            (1, "B", 1),
            (1, "A", 3),
            (1, "A", 3),
            (2, "A", 1),
            (2, "B", 2),
            (3, "A", 1),
            (4, "C", 1),
            (5, "Singleton", 1),
            (6, "A", 1),
            (6, "Rare", 1),
        ],
        columns=["order_id", "product_id", "remaining_quantity"],
    )


def test_directional_metrics_count_product_presence_once(baskets: pd.DataFrame) -> None:
    before = baskets.copy(deep=True)
    result = build_basket_rules(baskets, min_support=1 / 3, min_product_baskets=2)

    assert list(result.itertuples(index=False, name=None)) == [
        ("B", "A", 2, 1 / 3, 1.0, 1.5),
        ("A", "B", 2, 1 / 3, 0.5, 1.5),
    ]
    assert_frame_equal(
        build_basket_rules(
            baskets.iloc[::-1], min_support=1 / 3, min_product_baskets=2
        ),
        result,
    )
    assert_frame_equal(baskets, before)


def test_rare_product_filter_is_independent_of_pair_support(
    baskets: pd.DataFrame,
) -> None:
    unfiltered = build_basket_rules(baskets, min_support=1 / 6, min_product_baskets=1)
    filtered = build_basket_rules(baskets, min_support=1 / 6, min_product_baskets=2)

    assert "Rare" in set(unfiltered["consequent"])
    assert set(zip(filtered["antecedent"], filtered["consequent"])) == {
        ("A", "B"),
        ("B", "A"),
    }


def test_support_above_pair_frequency_excludes_pair(baskets: pd.DataFrame) -> None:
    assert build_basket_rules(baskets, min_support=0.34, min_product_baskets=2).empty


def test_single_product_and_empty_baskets_return_same_schema(
    baskets: pd.DataFrame,
) -> None:
    single_product = baskets[baskets["product_id"] == "A"]
    result = build_basket_rules(single_product, min_product_baskets=1)

    assert result.empty
    assert list(result) == [
        "antecedent",
        "consequent",
        "basket_count",
        "support",
        "confidence",
        "lift",
    ]
    assert_frame_equal(result, build_basket_rules(baskets.iloc[:0]))


@pytest.mark.parametrize("support", [-0.01, 1.01, float("nan")])
def test_invalid_support_is_rejected(baskets: pd.DataFrame, support: float) -> None:
    with pytest.raises(ValueError, match="min_support"):
        build_basket_rules(baskets, min_support=support)


def test_invalid_product_basket_minimum_is_rejected(baskets: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="min_product_baskets"):
        build_basket_rules(baskets, min_product_baskets=0)


def test_missing_product_id_is_rejected(baskets: pd.DataFrame) -> None:
    invalid = baskets.assign(product_id=baskets["product_id"].mask(baskets.index == 0))
    with pytest.raises(ValueError, match="product_id"):
        build_basket_rules(invalid)
