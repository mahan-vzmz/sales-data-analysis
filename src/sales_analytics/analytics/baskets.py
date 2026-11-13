"""Directional product-pair rules from completed Gold order baskets."""

from collections import Counter
from itertools import combinations

import pandas as pd


def build_basket_rules(
    baskets: pd.DataFrame, *, min_support: float = 0.01, min_product_baskets: int = 5
) -> pd.DataFrame:
    """Rank rules from order_id and product_id in gold.mart_basket_base."""
    if not 0 <= min_support <= 1:
        raise ValueError("min_support must be between 0 and 1")
    if min_product_baskets < 1:
        raise ValueError("min_product_baskets must be at least 1")

    products = baskets[["order_id", "product_id"]].drop_duplicates()
    if products.isna().any().any():
        raise ValueError("Basket rows require non-null order_id and product_id")

    total_baskets = products["order_id"].nunique()
    product_counts = products["product_id"].value_counts()
    eligible = products.loc[
        products["product_id"].map(product_counts).ge(min_product_baskets)
    ]
    pair_counts: Counter[tuple[str, str]] = Counter()
    for _, basket in eligible.groupby("order_id", sort=False):
        pair_counts.update(combinations(sorted(basket["product_id"]), 2))

    rows = []
    for (left, right), basket_count in pair_counts.items():
        support = basket_count / total_baskets
        if support < min_support:
            continue
        lift = (basket_count * total_baskets) / (
            int(product_counts[left]) * int(product_counts[right])
        )
        for antecedent, consequent in ((left, right), (right, left)):
            confidence = basket_count / int(product_counts[antecedent])
            rows.append(
                (antecedent, consequent, basket_count, support, confidence, lift)
            )

    rules = pd.DataFrame(
        rows,
        columns=[
            "antecedent",
            "consequent",
            "basket_count",
            "support",
            "confidence",
            "lift",
        ],
    )
    return rules.sort_values(
        ["lift", "confidence", "support", "antecedent", "consequent"],
        ascending=[False, False, False, True, True],
        ignore_index=True,
    )
