from pathlib import Path

import pandas as pd
import pytest

from sales_analytics.config import Settings
from sales_analytics.legacy_pipeline import clean_data, load_raw_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings.from_root(tmp_path)


@pytest.fixture(scope="session")
def raw_v1_df() -> pd.DataFrame:
    return load_raw_data(PROJECT_ROOT / "data" / "raw" / "sales_data.xlsx")


@pytest.fixture(scope="session")
def clean_v1_result(
    raw_v1_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return clean_data(raw_v1_df)


@pytest.fixture(scope="session")
def clean_v1_df(
    clean_v1_result: tuple[pd.DataFrame, pd.DataFrame],
) -> pd.DataFrame:
    return clean_v1_result[0]


@pytest.fixture(scope="session")
def cleaning_log_v1(
    clean_v1_result: tuple[pd.DataFrame, pd.DataFrame],
) -> pd.DataFrame:
    return clean_v1_result[1]
