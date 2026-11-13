# Customer inactivity propensity

The model estimates the probability of zero completed purchases in the
120 days after a customer snapshot. Customers enter the dataset after their
first completed purchase. The label measures a fixed period of inactivity.

## Reference data and evaluation

The run used the repository's synthetic generator fixture with seed 42 and
100 customers. Error injection and returns were disabled so completion was
known on the order date. The monthly cutoffs range from March 2023 through
June 2025. The 120-day horizon approximates four months, which spans the
interval implied by about three annual orders for active customers in year
three. The dataset version is `synthetic-seed-42-no-returns`.

| Split | Snapshot cutoffs | Last label date | Rows | Inactivity rate |
| --- | --- | --- | ---: | ---: |
| Training | 2023-03-31 to 2024-01-31 | 2024-05-30 | 488 | 83.0% |
| Validation | 2024-06-30 to 2024-08-31 | 2024-12-29 | 300 | 53.0% |
| Test | 2025-01-31 to 2025-06-30 | 2025-10-28 | 600 | 65.8% |

Validation starts on 2024-06-01 and test starts on 2025-01-01. Rows whose
label windows reach the next split are excluded. The latest feature event
must be on or before its snapshot cutoff. Models use only recency, completed
order count, and return count. Segment is used for reporting.

## Methods and results

The majority baseline uses the training prevalence as a constant
probability. The recency baseline uses training prevalence within 90-day
recency bands, falling back to overall training prevalence for unseen bands.
Candidates use fixed settings and fit only on training data. Logistic
regression uses L2 regularization with C=1. Random Forest uses 50 trees,
maximum depth five, at least 10 rows per leaf, and seed 42.

| Method | Validation Brier | Test Brier | Test ROC-AUC | Test PR-AUC (AP) |
| --- | ---: | ---: | ---: | ---: |
| Majority | 0.3391 | 0.2544 | 0.5000 | 0.6583 |
| Recency | 0.3235 | 0.2603 | 0.5265 | 0.6609 |
| Logistic regression | 0.3264 | 0.2995 | 0.3711 | 0.6327 |
| Random Forest | 0.3227 | 0.2655 | 0.3567 | 0.5977 |

Lower Brier is better. Validation nominated Random Forest and selected
recency as the fallback. Random Forest failed the one-time test gate against
recency, so the released evaluation artifact keeps the recency baseline.
The majority baseline had the lowest test Brier. The fallback was fixed
before that comparison. PR-AUC is reported as average precision.

## Calibration and limitations

For the selected baseline, 494 of 600 test rows fell in the 0.8–0.9
probability bin. Their mean predicted probability was 85.1% and their
observed inactivity rate was 66.8%. Consumer had the highest segment Brier
at 0.3138 across 192 rows. The prevalence shift and repeated customers make
this a temporal evaluation of the fixture. It gives limited evidence about
unseen customers or production populations. Return count is constant in
this run. For feeds with returns, event availability must be recorded at
the time it becomes known.

The integration test reproduces this split with
`python -m pytest tests/integration/test_propensity_training.py -q`.
`write_propensity_artifact` exports held-out probabilities, calibration,
segment errors, and evaluation metadata in JSON. Model version is `1`.
