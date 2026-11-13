"""Cached reads from approved Gold marts and local model artifacts."""

import json
from dataclasses import replace
from datetime import date
from os import environ
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import streamlit as st

from app.ui.filters import Filters
from sales_analytics.config import Settings

MART_DIMENSIONS: dict[str, dict[str, str]] = {
    "mart_executive": {},
    "mart_customer_360": {"geography": "home_city"},
    "mart_cohort_base": {"date": "order_date"},
    "mart_basket_base": {"date": "order_date", "category": "category"},
    "mart_forecasting_base": {"date": "week_start", "category": "category"},
}
_ARTIFACT_FILES = {"forecast": "forecast.json", "propensity": "propensity.json"}


class DataUnavailable(RuntimeError):
    """An expected data problem with a message suitable for the UI."""


def app_settings() -> Settings:
    """Use project paths by default, with deployment overrides."""
    paths = Settings.from_root(Path(__file__).resolve().parents[2])
    return replace(
        paths,
        warehouse_path=Path(
            environ.get("SALES_DUCKDB_PATH", str(paths.warehouse_path))
        ),
        model_dir=Path(environ.get("SALES_MODEL_DIR", str(paths.model_dir))),
    )


@st.cache_data(ttl=300, max_entries=128, show_spinner=False)
def _query_gold(
    path: str,
    revision: tuple[int, int, int],
    sql: str,
    parameters: tuple[date | str, ...],
) -> pd.DataFrame:
    with duckdb.connect(path, read_only=True) as connection:
        return connection.execute(sql, parameters).df()


def read_mart(
    settings: Settings, mart: str, filters: Filters = Filters()
) -> pd.DataFrame:
    """Return mart rows matching a parameterized filter."""
    if mart not in MART_DIMENSIONS:
        raise ValueError(f"Unknown Gold mart: {mart}")
    dimensions = MART_DIMENSIONS[mart]
    conditions: list[str] = []
    parameters: list[date | str] = []
    for bound, operator in ((filters.start, ">="), (filters.end, "<=")):
        if bound is not None:
            if "date" not in dimensions:
                raise ValueError(f"{mart} does not support the date filter")
            conditions.append(f"{dimensions['date']} {operator} ?")
            parameters.append(bound)
    for dimension, values in (
        ("channel", filters.channels),
        ("category", filters.categories),
        ("geography", filters.geographies),
    ):
        if values:
            if dimension not in dimensions:
                raise ValueError(f"{mart} does not support the {dimension} filter")
            placeholders = ", ".join("?" for _ in values)
            conditions.append(f"{dimensions[dimension]} in ({placeholders})")
            parameters.extend(values)

    sql = f"select * from gold.{mart}"
    if conditions:
        sql += " where " + " and ".join(conditions)
    path = settings.warehouse_path.resolve()
    try:
        stat = path.stat()
        return _query_gold(
            str(path),
            (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size),
            sql,
            tuple(parameters),
        )
    except FileNotFoundError as exc:
        raise DataUnavailable(
            "The warehouse file is missing. Build Gold data first."
        ) from exc
    except duckdb.CatalogException as exc:
        raise DataUnavailable(
            f"Gold mart {mart} is missing or incomplete. Build Gold data first."
        ) from exc
    except (duckdb.Error, OSError) as exc:
        raise DataUnavailable(
            "The warehouse could not be read. Check that the file is accessible and no build is writing to it."
        ) from exc


def load_model_artifact(settings: Settings, model: str) -> dict[str, Any]:
    """Load a named evaluation artifact from the configured model directory."""
    if model not in _ARTIFACT_FILES:
        raise ValueError(f"Unknown model artifact: {model}")
    path = settings.model_dir / _ARTIFACT_FILES[model]
    label = f"{model.capitalize()} artifact"
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DataUnavailable(
            f"{label} is missing. Generate it with the model evaluation."
        ) from exc
    except (OSError, ValueError) as exc:
        raise DataUnavailable(f"{label} could not be read.") from exc
    if not isinstance(artifact, dict) or not isinstance(artifact.get("model"), str):
        raise DataUnavailable(f"{label} has an unexpected format.")
    return artifact
