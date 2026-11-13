from datetime import date

import pandas as pd
import pytest

from sales_analytics.ml.propensity import (
    calibration_table,
    majority_probability,
    recency_probability,
    split_snapshots,
)


def test_split_purges_labels_reaching_the_next_period() -> None:
    snapshots = pd.DataFrame(
        {
            "cutoff": pd.to_datetime(
                ["2025-03-01", "2025-01-01", "2025-02-01", "2025-01-20", "2025-02-20"]
            ),
            "horizon_end": pd.to_datetime(
                ["2025-03-13", "2025-01-13", "2025-02-13", "2025-02-01", "2025-03-04"]
            ),
            "last_feature_event_date": pd.to_datetime(
                ["2025-03-01", "2025-01-01", "2025-02-01", "2025-01-20", "2025-02-20"]
            ),
        }
    )
    train, validation, test = split_snapshots(
        snapshots, date(2025, 2, 1), date(2025, 3, 1)
    )
    assert list(train.index) == [1]
    assert list(validation.index) == [2]
    assert list(test.index) == [0]
    assert train["horizon_end"].max() < validation["cutoff"].min()
    assert validation["horizon_end"].max() < test["cutoff"].min()
    snapshots.loc[0, "last_feature_event_date"] = pd.Timestamp("2025-03-02")
    with pytest.raises(ValueError, match="feature"):
        split_snapshots(snapshots, date(2025, 2, 1), date(2025, 3, 1))


def test_baselines_use_training_prevalence_and_recency_bands() -> None:
    train = pd.DataFrame(
        {"recency_days": [0, 89, 90, 179], "inactive_label": [0, 0, 1, 0]}
    )
    future = pd.Series([179, 180, 0])
    assert majority_probability(train) == 0.25
    assert recency_probability(train, future).tolist() == [0.5, 0.25, 0.0]


def test_calibration_table_accounts_for_zero_and_one() -> None:
    table = calibration_table(pd.Series([0, 1, 1]), pd.Series([0.0, 0.1, 1.0]))
    assert table["count"].tolist() == [1, 1, 1]
    assert table["mean_probability"].tolist() == [0.0, 0.1, 1.0]
    assert table["observed_rate"].tolist() == [0.0, 1.0, 1.0]
