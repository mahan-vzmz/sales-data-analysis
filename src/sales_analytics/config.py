"""Central project paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Immutable paths derived from a project root."""

    project_root: Path
    source_dir: Path
    warehouse_path: Path
    report_dir: Path
    model_dir: Path
    dbt_project_dir: Path

    @classmethod
    def from_root(cls, root: Path) -> Settings:
        project_root = root.resolve()
        return cls(
            project_root=project_root,
            source_dir=project_root / "data" / "source",
            warehouse_path=project_root / "warehouse" / "sales.duckdb",
            report_dir=project_root / "reports",
            model_dir=project_root / "models",
            dbt_project_dir=project_root / "analytics_dbt",
        )
