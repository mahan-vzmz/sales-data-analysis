from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sales_analytics.config import Settings


def test_settings_build_all_paths_from_project_root(tmp_path: Path) -> None:
    settings = Settings.from_root(tmp_path)

    assert settings.project_root == tmp_path.resolve()
    assert settings.source_dir == tmp_path / "data" / "source"
    assert settings.warehouse_path == tmp_path / "warehouse" / "sales.duckdb"
    assert settings.report_dir == tmp_path / "reports"
    assert settings.model_dir == tmp_path / "models"
    assert settings.dbt_project_dir == tmp_path / "analytics_dbt"


def test_settings_are_immutable(tmp_path: Path) -> None:
    settings = Settings.from_root(tmp_path)

    with pytest.raises(FrozenInstanceError):
        settings.project_root = tmp_path / "other"  # type: ignore[misc]
