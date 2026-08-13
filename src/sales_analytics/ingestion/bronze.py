"""DuckDB Bronze and audit infrastructure."""

from pathlib import Path

import duckdb

SCHEMAS = ("bronze", "silver", "gold", "audit")

INGESTION_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS audit.ingestion_runs (
    load_id VARCHAR PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    source_manifest_hash VARCHAR NOT NULL,
    source_row_count BIGINT NOT NULL DEFAULT 0 CHECK (source_row_count >= 0),
    valid_row_count BIGINT NOT NULL DEFAULT 0 CHECK (valid_row_count >= 0),
    invalid_row_count BIGINT NOT NULL DEFAULT 0 CHECK (invalid_row_count >= 0),
    error_summary VARCHAR,
    CHECK (valid_row_count + invalid_row_count <= source_row_count),
    CHECK (
        (status = 'running' AND completed_at IS NULL AND error_summary IS NULL)
        OR
        (status = 'succeeded' AND completed_at IS NOT NULL AND error_summary IS NULL)
        OR
        (status = 'failed' AND completed_at IS NOT NULL AND error_summary IS NOT NULL)
    )
)
"""

VALIDATION_FAILURES_DDL = """
CREATE TABLE IF NOT EXISTS audit.validation_failures (
    load_id VARCHAR NOT NULL REFERENCES audit.ingestion_runs(load_id),
    source_file VARCHAR NOT NULL,
    source_table VARCHAR NOT NULL,
    source_row BIGINT,
    check_name VARCHAR NOT NULL,
    column_name VARCHAR,
    failure_case VARCHAR,
    recorded_at TIMESTAMP NOT NULL DEFAULT current_timestamp
)
"""


def bootstrap_warehouse(path: Path) -> None:
    """Create the persistent warehouse objects required by ingestion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as connection:
        connection.begin()
        try:
            for schema in SCHEMAS:
                connection.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            connection.execute(INGESTION_RUNS_DDL)
            connection.execute(VALIDATION_FAILURES_DDL)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
