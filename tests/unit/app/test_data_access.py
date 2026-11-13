from datetime import date
from pathlib import Path
from subprocess import run
from sys import executable

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

from app.ui.data import DataUnavailable, load_model_artifact, read_mart
from app.ui.filters import Filters
from sales_analytics.config import Settings

APP = Path(__file__).parents[3] / "app" / "streamlit_app.py"


def test_entrypoint_runs_without_project_root_on_import_path(tmp_path: Path) -> None:
    result = run(
        [
            executable,
            "-I",
            "-c",
            "import sys; from pathlib import Path; "
            "from streamlit.testing.v1 import AppTest; "
            "sys.path.insert(0, str(Path(sys.argv[1]).parent)); "
            "assert not AppTest.from_file(sys.argv[1]).run().exception",
            str(APP),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    paths = Settings.from_root(tmp_path)
    paths.warehouse_path.parent.mkdir()
    with duckdb.connect(str(paths.warehouse_path)) as connection:
        connection.execute("create schema gold")
        connection.execute(
            """
            create table gold.mart_forecasting_base as
            select * from (values
                (date '2025-01-06', 'Audio', 4),
                (date '2025-01-13', 'Audio', 5),
                (date '2025-01-13', 'Accessories', 8)
            ) as weekly(week_start, category, ordered_quantity)
            """
        )
        connection.execute(
            "create table gold.mart_customer_360 as select 'Paris' as home_city"
        )
    return paths


def test_read_mart_binds_values_and_uses_read_only(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = duckdb.connect
    modes = []

    def connect(path, *, read_only=False):
        modes.append(read_only)
        return original(path, read_only=read_only)

    monkeypatch.setattr(duckdb, "connect", connect)
    first = Filters(
        start=date(2025, 1, 13), end=date(2025, 1, 13), categories=("Audio",)
    )
    assert read_mart(settings, "mart_forecasting_base", first)[
        "ordered_quantity"
    ].tolist() == [5]
    assert read_mart(settings, "mart_forecasting_base", first)[
        "ordered_quantity"
    ].tolist() == [5]
    hostile = Filters(categories=("Audio' OR 1=1 --",))
    assert read_mart(settings, "mart_forecasting_base", hostile).empty
    assert modes == [True, True]


def test_filters_use_supported_dimensions_only(settings: Settings) -> None:
    customers = read_mart(
        settings, "mart_customer_360", Filters(geographies=("Paris",))
    )
    assert customers["home_city"].tolist() == ["Paris"]
    with pytest.raises(ValueError, match="channel"):
        read_mart(settings, "mart_forecasting_base", Filters(channels=("Online",)))
    with pytest.raises(ValueError, match="mart"):
        read_mart(settings, "fact_sales")


def test_missing_data_and_artifact_are_reported(settings: Settings) -> None:
    with pytest.raises(DataUnavailable, match="Gold mart"):
        read_mart(settings, "mart_executive")
    with pytest.raises(DataUnavailable, match="Forecast artifact"):
        load_model_artifact(settings, "forecast")


def test_app_reports_empty_filter_result_and_missing_artifact(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SALES_DUCKDB_PATH", str(settings.warehouse_path))
    monkeypatch.setenv("SALES_MODEL_DIR", str(settings.model_dir))
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert any("Forecast artifact" in message.value for message in app.info)
    app.switch_page("app_pages/gold_data.py").run()
    assert not app.exception
    assert len(app.dataframe) == 1
    app.multiselect(key="gold_category").set_value(["Accessories"])
    app.date_input(key="gold_dates").set_value((date(2025, 1, 6), date(2025, 1, 6)))
    app.run()
    assert not app.exception
    assert any("No rows match" in message.value for message in app.info)
