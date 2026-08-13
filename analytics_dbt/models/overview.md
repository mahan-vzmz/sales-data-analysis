{% docs analytics_overview %}

# Analytics consumption layer

The `gold.mart_*` views are the supported boundary for dashboards, Python
analysis, and machine-learning workflows. Each mart declares its row grain and
owner in dbt metadata and is derived only from tested Gold facts and dimensions.

Use `mart_executive` for reconciled headline KPIs, `mart_customer_360` for
customer analysis, `mart_cohort_base` for retention, `mart_basket_base` for
product affinity, and `mart_forecasting_base` for gap-free weekly forecasting.
Bronze ingestion tables are intentionally excluded from this consumption layer.

Financial reconciliation uses a currency tolerance of 0.01. Forecast returns
are attributed to the original sale week so the weekly target represents
eventual demand value, not the operational timing of refund processing.

{% enddocs %}
