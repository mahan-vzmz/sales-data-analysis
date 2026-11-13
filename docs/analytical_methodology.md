# Analytical methodology

## RFM customer segmentation

`build_rfm(customers, analysis_date)` reads the `gold.mart_customer_360`
snapshot, with one row per customer.

| Metric | Definition | Better score |
| --- | --- | --- |
| Recency | Calendar days from the last completed purchase to the supplied analysis date | Fewer days |
| Frequency | Distinct orders with at least one unit retained after returns | More orders |
| Monetary value | Net sales less returned revenue in the snapshot | Higher value |

Each metric is ranked separately among customers with a completed purchase,
from weakest to strongest. Equal values share their average rank. For rank
`r` among `n` buyers, the score is `ceil(5 × (r − 0.5) / n)`. A sole
buyer or an entirely tied metric receives 3. Some quintiles can be empty.

Segment rules apply in this order:

1. **No completed purchases** — frequency is zero, including customers whose
   orders were all fully returned. Recency is missing and all scores are 0.
   Monetary value is preserved from the mart.
2. **Champions** — each of the three scores is at least 4.
3. **At risk** — recency score is 1 or 2.
4. **Active** — all other customers with a completed purchase.

The analysis date is a recency reference date. It must be on or after the
latest completed purchase in the input. Frequency and monetary value reflect
the entire supplied snapshot. Historical analysis requires a snapshot built
at the corresponding cutoff, with only data available by that date.

## Monthly cohort retention

`build_retention_matrix(purchases)` uses a complete `gold.mart_cohort_base`
snapshot. Customers enter the cohort for their first completed purchase month.
A completed purchase has at least one retained unit after returns. The mart
excludes fully returned orders, and the analysis also filters out rows with no
retained units before counting customers.

For each cohort age, divide the number of distinct cohort members with a
completed purchase that month by the original cohort size. Age is measured in
calendar months. Month zero is 100%, and multiple orders by the same customer
in a month count once. If one of two cohort members buys twice the next month,
month-one retention is 50%.

`CohortResult.long_form` provides the cohort month, age, cohort size, active
customer count, and retention rate as a fraction. `CohortResult.matrix` puts
cohort months on rows and ages on columns. Months with no purchases through
the latest eligible purchase month in the input have a zero rate. Later months
are omitted from the long-form table and appear blank where the matrix has
that age for older cohorts. The latest observed month may be partial. An input
with no eligible purchases produces empty outputs.

## Market basket analysis

`build_basket_rules(baskets)` reads `order_id` and `product_id` from
`gold.mart_basket_base`. The mart includes products with at least one unit
retained after returns. Each order is one basket, and each product counts at
most once per basket regardless of quantity.

| Metric | Definition for A → B |
| --- | --- |
| Basket count | Number of baskets containing both A and B |
| Support | Basket count divided by all baskets represented in the mart |
| Confidence | Basket count divided by baskets containing A |
| Lift | Confidence divided by the fraction of all baskets containing B |

Support and lift are the same in both directions. Confidence can differ.
Lift above 1 indicates that the products occur together more often than
expected from their individual frequencies.

By default, each product must appear in at least 5 baskets and the pair must
appear in at least 1% of all baskets. Both thresholds are inclusive. The
denominator includes every order with a retained product, including
single-product baskets and baskets containing only rare products. Rules are
sorted by descending lift, confidence, and support,
then by product IDs to break ties.

The synthetic integration check requires Laptop Pro → Wireless Mouse to reach
4% support, 35% confidence, and 1.3 lift. Its lift must also exceed Laptop Pro
→ Mechanical Keyboard and Laptop Pro → 27-inch Monitor. This check measures
recovery of a pattern built into the generator.
