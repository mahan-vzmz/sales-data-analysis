"""Directional basket rules for a potential cross-sell experiment."""

import streamlit as st

from app.ui.charts import show_download, show_empty_result
from app.ui.data import MART_DIMENSIONS, DataUnavailable, app_settings, read_mart
from app.ui.filters import sidebar_filters
from sales_analytics.analytics.baskets import build_basket_rules

st.title("Basket analysis")
st.caption(
    "Which retained products appear together often enough to test a cross-sell offer?"
)
settings = app_settings()
mart = "mart_basket_base"
try:
    source = read_mart(settings, mart)
    filters = sidebar_filters(source, MART_DIMENSIONS[mart])
    baskets = read_mart(settings, mart, filters)
except DataUnavailable as exc:
    st.info(str(exc))
    st.stop()
if baskets.empty:
    show_empty_result()
    st.stop()

with st.container(horizontal=True):
    support = st.slider("Minimum support", 0.0, 1.0, 0.01, 0.01, key="min_support")
    confidence = st.slider(
        "Minimum confidence", 0.0, 1.0, 0.0, 0.01, key="min_confidence"
    )
    lift = st.number_input(
        "Minimum lift", min_value=0.0, value=1.0, step=0.1, key="min_lift"
    )
    count = st.number_input(
        "Minimum baskets per product", min_value=1, value=1, key="min_product_baskets"
    )
rules = build_basket_rules(baskets, min_support=support, min_product_baskets=count)
rules = rules.loc[rules["confidence"].ge(confidence) & rules["lift"].ge(lift)].copy()
if rules.empty:
    st.info(
        "No rules match these thresholds. Lower a threshold or widen the basket selection."
    )
    st.stop()

names = baskets.drop_duplicates("product_id").set_index("product_id")["product_name"]
rules["antecedent_name"] = rules["antecedent"].map(names)
rules["consequent_name"] = rules["consequent"].map(names)
st.caption(
    f"Support uses all {baskets['order_id'].nunique():,} orders represented in the filtered basket rows."
)
top = rules.iloc[0]
if top["lift"] > 1:
    st.write(
        "First pair to investigate", top["antecedent_name"], "→", top["consequent_name"]
    )
show_download(
    rules,
    "basket-rules.csv",
    alt="Directional product-pair support, confidence and lift",
)
