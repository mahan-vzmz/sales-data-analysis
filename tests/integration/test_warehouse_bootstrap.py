from pathlib import Path

import duckdb
import pytest

from sales_analytics.ingestion.bronze import bootstrap_warehouse


def test_bootstrap_is_idempotent_and_creates_medallion_audit_objects(
    tmp_path: Path,
) -> None:
    warehouse_path = tmp_path / "warehouse" / "sales.duckdb"

    bootstrap_warehouse(warehouse_path)
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path), read_only=True) as connection:
        schemas = {
            row[0]
            for row in connection.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()
        }
        audit_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'audit'
                """
            ).fetchall()
        }
        run_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'audit'
                  AND table_name = 'ingestion_runs'
                """
            ).fetchall()
        }
        failure_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'audit'
                  AND table_name = 'validation_failures'
                """
            ).fetchall()
        }

    assert {"bronze", "silver", "gold", "audit"} <= schemas
    assert audit_tables == {"ingestion_runs", "validation_failures"}
    assert run_columns == {
        "load_id",
        "started_at",
        "completed_at",
        "status",
        "source_manifest_hash",
        "source_row_count",
        "valid_row_count",
        "invalid_row_count",
        "error_summary",
    }
    assert failure_columns == {
        "load_id",
        "source_file",
        "source_table",
        "source_row",
        "check_name",
        "column_name",
        "failure_case",
        "recorded_at",
    }


def test_audit_run_states_require_failure_details_and_preserve_history(
    tmp_path: Path,
) -> None:
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        connection.execute(
            """
            INSERT INTO audit.ingestion_runs VALUES
                (
                    'load-success',
                    TIMESTAMP '2026-08-13 09:00:00',
                    TIMESTAMP '2026-08-13 09:01:00',
                    'succeeded',
                    'manifest-a',
                    100,
                    98,
                    2,
                    NULL
                ),
                (
                    'load-failed',
                    TIMESTAMP '2026-08-13 10:00:00',
                    TIMESTAMP '2026-08-13 10:00:05',
                    'failed',
                    'manifest-b',
                    0,
                    0,
                    0,
                    'source file was incomplete'
                )
            """
        )

        with pytest.raises(duckdb.ConstraintException):
            connection.execute(
                """
                INSERT INTO audit.ingestion_runs VALUES (
                    'load-invalid-failure',
                    TIMESTAMP '2026-08-13 11:00:00',
                    TIMESTAMP '2026-08-13 11:00:01',
                    'failed',
                    'manifest-c',
                    0,
                    0,
                    0,
                    NULL
                )
                """
            )

        runs = connection.execute(
            """
            SELECT load_id, status, error_summary
            FROM audit.ingestion_runs
            ORDER BY started_at
            """
        ).fetchall()

    assert runs == [
        ("load-success", "succeeded", None),
        ("load-failed", "failed", "source file was incomplete"),
    ]
