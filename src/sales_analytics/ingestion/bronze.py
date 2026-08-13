"""DuckDB Bronze and audit infrastructure."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import duckdb
import pandas as pd

from sales_analytics.generation.generator import GeneratedDataset
from sales_analytics.ingestion.contracts import SOURCE_TABLES
from sales_analytics.ingestion.validate import (
    ValidationResult,
    source_manifest_hash,
)

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


@dataclass(frozen=True)
class IngestionSummary:
    """Outcome of one requested Bronze ingestion."""

    load_id: str
    source_manifest_hash: str
    status: Literal["succeeded", "skipped"]
    source_row_count: int
    valid_row_count: int
    invalid_row_count: int
    failure_count: int


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


def ingest_to_bronze(
    dataset: GeneratedDataset,
    validation: ValidationResult,
    connection: duckdb.DuckDBPyConnection,
    load_id: str,
) -> IngestionSummary:
    """Persist one raw dataset and its validation lineage atomically."""
    manifest_hash = source_manifest_hash(dataset)
    if validation.load_id != load_id:
        raise ValueError("validation load_id does not match ingestion load_id")
    if validation.source_manifest_hash != manifest_hash:
        raise ValueError("validation dataset manifest does not match ingestion dataset")
    source_row_count = sum(len(getattr(dataset, table)) for table in SOURCE_TABLES)
    valid_row_count = int(validation.summary["valid_rows"].sum())
    invalid_row_count = int(validation.summary["invalid_rows"].sum())
    ingested_at = datetime.now(UTC).replace(tzinfo=None)
    existing_manifest = connection.execute(
        """
        SELECT 1
        FROM audit.ingestion_runs
        WHERE source_manifest_hash = ? AND status = 'succeeded'
        LIMIT 1
        """,
        [manifest_hash],
    ).fetchone()
    if existing_manifest is not None:
        return _summary(
            load_id,
            manifest_hash,
            "skipped",
            source_row_count,
            valid_row_count,
            invalid_row_count,
            len(validation.failure_cases),
        )

    if (
        connection.execute(
            "SELECT 1 FROM audit.ingestion_runs WHERE load_id = ?", [load_id]
        ).fetchone()
        is not None
    ):
        raise ValueError(f"load_id already exists: {load_id}")

    connection.begin()
    try:
        connection.execute(
            """
            INSERT INTO audit.ingestion_runs (
                load_id,
                started_at,
                status,
                source_manifest_hash,
                source_row_count,
                valid_row_count,
                invalid_row_count
            )
            VALUES (?, ?, 'running', ?, ?, ?, ?)
            """,
            [
                load_id,
                ingested_at,
                manifest_hash,
                source_row_count,
                valid_row_count,
                invalid_row_count,
            ],
        )
        for table in SOURCE_TABLES:
            _load_source_table(
                connection,
                table,
                getattr(dataset, table),
                load_id,
                ingested_at,
            )
        _load_validation_failures(connection, validation, load_id)
        connection.execute(
            """
            UPDATE audit.ingestion_runs
            SET status = 'succeeded', completed_at = ?
            WHERE load_id = ?
            """,
            [datetime.now(UTC).replace(tzinfo=None), load_id],
        )
        connection.commit()
    except Exception as error:
        connection.rollback()
        _record_failed_run(
            connection,
            load_id,
            ingested_at,
            manifest_hash,
            source_row_count,
            error,
        )
        raise

    return _summary(
        load_id,
        manifest_hash,
        "succeeded",
        source_row_count,
        valid_row_count,
        invalid_row_count,
        len(validation.failure_cases),
    )


def _load_source_table(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    source: pd.DataFrame,
    load_id: str,
    ingested_at: datetime,
) -> None:
    batch = source.copy(deep=True)
    if table == "returns" and batch.empty:
        batch["return_date"] = pd.to_datetime(batch["return_date"])
    batch["_load_id"] = load_id
    batch["_source_file"] = f"{table}.csv"
    batch["_source_row"] = source.index
    batch["_ingested_at"] = ingested_at
    connection.register("_bronze_batch", batch)
    try:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS bronze.{table} AS
            SELECT * FROM _bronze_batch WHERE false
            """
        )
        connection.execute(
            f"INSERT INTO bronze.{table} BY NAME SELECT * FROM _bronze_batch"
        )
    finally:
        connection.unregister("_bronze_batch")


def _load_validation_failures(
    connection: duckdb.DuckDBPyConnection,
    validation: ValidationResult,
    load_id: str,
) -> None:
    if validation.failure_cases.empty:
        return

    failures = validation.failure_cases.copy(deep=True)
    failures["load_id"] = load_id
    failures.insert(
        1,
        "source_file",
        failures["source_table"].map(lambda table: f"{table}.csv"),
    )
    for column in ("check_name", "column_name", "failure_case"):
        failures[column] = failures[column].map(
            lambda value: None if pd.isna(value) else str(value)
        )
    connection.register("_validation_failures", failures)
    try:
        connection.execute(
            """
            INSERT INTO audit.validation_failures BY NAME
            SELECT * FROM _validation_failures
            """
        )
    finally:
        connection.unregister("_validation_failures")


def _record_failed_run(
    connection: duckdb.DuckDBPyConnection,
    load_id: str,
    started_at: datetime,
    manifest_hash: str,
    source_row_count: int,
    error: Exception,
) -> None:
    connection.begin()
    try:
        connection.execute(
            """
            INSERT INTO audit.ingestion_runs (
                load_id,
                started_at,
                completed_at,
                status,
                source_manifest_hash,
                source_row_count,
                valid_row_count,
                invalid_row_count,
                error_summary
            )
            VALUES (?, ?, ?, 'failed', ?, ?, 0, 0, ?)
            """,
            [
                load_id,
                started_at,
                datetime.now(UTC).replace(tzinfo=None),
                manifest_hash,
                source_row_count,
                str(error) or type(error).__name__,
            ],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _summary(
    load_id: str,
    manifest_hash: str,
    status: Literal["succeeded", "skipped"],
    source_row_count: int,
    valid_row_count: int,
    invalid_row_count: int,
    failure_count: int,
) -> IngestionSummary:
    return IngestionSummary(
        load_id=load_id,
        source_manifest_hash=manifest_hash,
        status=status,
        source_row_count=source_row_count,
        valid_row_count=valid_row_count,
        invalid_row_count=invalid_row_count,
        failure_count=failure_count,
    )
