from datetime import date

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from sales_analytics.analytics.churn import build_customer_snapshots

CUTOFF = date(2025, 1, 10)


@pytest.fixture
def events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("at_cutoff", "2025-01-10", "completed_purchase"),
            ("at_horizon", "2025-01-08", "completed_purchase"),
            ("at_horizon", "2025-01-15", "completed_purchase"),
            ("after_horizon", "2025-01-05", "completed_purchase"),
            ("after_horizon", "2025-01-16", "completed_purchase"),
            ("only_returns_in_window", "2025-01-06", "completed_purchase"),
            ("only_returns_in_window", "2025-01-09", "return"),
            ("only_returns_in_window", "2025-01-11", "return"),
            ("return_only_customer", "2025-01-07", "return"),
            ("new_customer", "2025-01-11", "completed_purchase"),
        ],
        columns=["customer_id", "event_date", "event_type"],
    )


def test_snapshot_label_boundaries_and_eligible_population(
    events: pd.DataFrame,
) -> None:
    snapshot = build_customer_snapshots(events, [CUTOFF], 5).set_index("customer_id")

    assert snapshot["inactive_label"].to_dict() == {
        "after_horizon": 1,
        "at_cutoff": 1,
        "at_horizon": 0,
        "only_returns_in_window": 1,
    }
    assert snapshot.loc["at_cutoff", "recency_days"] == 0
    assert snapshot.loc["at_horizon", "recency_days"] == 2
    assert snapshot["completed_order_count"].tolist() == [1, 1, 1, 1]
    assert snapshot["return_count"].to_dict()["only_returns_in_window"] == 1
    assert snapshot["horizon_end"].eq(pd.Timestamp("2025-01-15")).all()


def test_future_events_can_change_labels_without_changing_features(
    events: pd.DataFrame,
) -> None:
    original = events.copy(deep=True)
    prefix = events[events["event_date"] <= "2025-01-10"]
    full = build_customer_snapshots(events, [CUTOFF], 5)
    past = build_customer_snapshots(
        prefix, [CUTOFF], 5, observation_end=date(2025, 1, 15)
    )

    assert full["last_feature_event_date"].le(full["cutoff"]).all()
    assert_frame_equal(
        full.drop(columns="inactive_label"), past.drop(columns="inactive_label")
    )
    assert full.set_index("customer_id").loc["at_horizon", "inactive_label"] == 0
    assert past.set_index("customer_id").loc["at_horizon", "inactive_label"] == 1
    assert_frame_equal(events, original)


def test_customers_can_enter_later_snapshots(events: pd.DataFrame) -> None:
    later = date(2025, 1, 11)
    result = build_customer_snapshots(events, [later, CUTOFF, later], 5)
    new_customer = result[result["customer_id"] == "new_customer"]
    repeated = result[result["customer_id"] == "only_returns_in_window"]

    assert new_customer["cutoff"].tolist() == [pd.Timestamp(later)]
    assert new_customer["recency_days"].tolist() == [0]
    assert repeated["return_count"].tolist() == [1, 2]
    assert repeated["last_feature_event_date"].tolist() == list(
        pd.to_datetime(["2025-01-09", "2025-01-11"])
    )
    assert not result.duplicated(["customer_id", "cutoff"]).any()


def test_incomplete_horizon_requires_an_observation_end(events: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="observation_end"):
        build_customer_snapshots(events, [date(2025, 1, 12)], 5)

    observed = build_customer_snapshots(
        events, [date(2025, 1, 12)], 5, observation_end=date(2025, 1, 17)
    )
    assert observed["horizon_end"].eq(pd.Timestamp("2025-01-17")).all()


def test_empty_or_return_only_history_has_no_customer_snapshots(
    events: pd.DataFrame,
) -> None:
    returned = events[events["event_type"] == "return"]
    kwargs = {"observation_end": date(2025, 1, 15)}

    empty = build_customer_snapshots(events.iloc[:0], [CUTOFF], 5, **kwargs)
    assert empty.empty
    assert "inactive_label" in empty
    assert_frame_equal(empty, build_customer_snapshots(returned, [CUTOFF], 5, **kwargs))


@pytest.mark.parametrize("horizon", [0, -1])
def test_horizon_must_be_positive(events: pd.DataFrame, horizon: int) -> None:
    with pytest.raises(ValueError, match="horizon_days"):
        build_customer_snapshots(events, [CUTOFF], horizon)


def test_numeric_warehouse_date_keys_are_rejected() -> None:
    events = pd.DataFrame(
        {
            "customer_id": ["A", "A"],
            "event_date": [20250110, 20250112],
            "event_type": ["completed_purchase", "completed_purchase"],
        }
    )

    with pytest.raises(ValueError, match="event_date"):
        build_customer_snapshots(events, [CUTOFF], 5, observation_end=date(2025, 1, 15))
