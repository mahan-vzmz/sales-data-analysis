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
