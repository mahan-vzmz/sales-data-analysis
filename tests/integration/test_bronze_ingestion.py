from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from sales_analytics.generation.generator import (
    GeneratedDataset,
    GeneratorConfig,
    generate_dataset,
)
from sales_analytics.ingestion.bronze import (
    bootstrap_warehouse,
    ingest_to_bronze,
)
from sales_analytics.ingestion.validate import validate_sources

SOURCE_TABLES = (
    "customers",
    "products",
    "orders",
    "order_items",
    "returns",
    "promotions",
    "calendar_events",
)
METADATA_COLUMNS = ("_load_id", "_source_file", "_source_row", "_ingested_at")
PROJECT_ROOT = Path(__file__).parents[2]


def _dataset(error_rate: float = 0.01) -> GeneratedDataset:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    config = replace(
        configured,
        customer_count=10,
        error_rates={name: error_rate for name in configured.error_rates},
    )
    return generate_dataset(config)


def _normalize_dates(stored: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    normalized = stored.copy()
    for column in source.columns:
        non_null = source[column].dropna()
        if (
            not non_null.empty
            and isinstance(non_null.iloc[0], date)
            and not isinstance(non_null.iloc[0], pd.Timestamp)
        ):
            normalized[column] = normalized[column].dt.date
    return normalized


def _content_hash(frame: pd.DataFrame) -> str:
    row_hashes = pd.util.hash_pandas_object(frame, index=False)
    return sha256(np.asarray(row_hashes).tobytes()).hexdigest()


def test_bronze_preserves_every_raw_row_and_adds_lineage(tmp_path: Path) -> None:
    dataset = _dataset()
    original_sources = {
        table: getattr(dataset, table).copy(deep=True) for table in SOURCE_TABLES
    }
    validation = validate_sources(dataset, load_id="load-exact")
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        summary = ingest_to_bronze(
            dataset, validation, connection, load_id="load-exact"
        )

        for table in SOURCE_TABLES:
            source = getattr(dataset, table).reset_index(drop=True)
            source_columns = ", ".join(f'"{column}"' for column in source.columns)
            stored = connection.execute(
                f"""
                SELECT {source_columns}
                FROM bronze.{table}
                WHERE _load_id = 'load-exact'
                ORDER BY _source_row
                """
            ).fetchdf()
            stored = _normalize_dates(stored, source)
            metadata = connection.execute(
                f"""
                SELECT _load_id, _source_file, _source_row, _ingested_at
                FROM bronze.{table}
                WHERE _load_id = 'load-exact'
                ORDER BY _source_row
                """
            ).fetchdf()

            assert len(stored) == len(source)
            assert _content_hash(stored) == _content_hash(source)
            pd.testing.assert_frame_equal(stored, source, check_dtype=False)
            assert tuple(metadata.columns) == METADATA_COLUMNS
            assert set(metadata["_load_id"]) <= {"load-exact"}
            assert set(metadata["_source_file"]) <= {f"{table}.csv"}
            assert metadata["_source_row"].tolist() == list(source.index)
            assert metadata["_ingested_at"].notna().all()

    assert summary.status == "succeeded"
    assert summary.source_row_count == sum(
        len(getattr(dataset, table)) for table in SOURCE_TABLES
    )
    assert summary.invalid_row_count == int(validation.summary["invalid_rows"].sum())
    for table, original in original_sources.items():
        pd.testing.assert_frame_equal(getattr(dataset, table), original)


def test_validation_failures_are_traceable_to_raw_bronze_rows(
    tmp_path: Path,
) -> None:
    dataset = _dataset()
    validation = validate_sources(dataset, load_id="load-rejected")
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        ingest_to_bronze(dataset, validation, connection, load_id="load-rejected")
        failures = connection.execute(
            """
            SELECT
                load_id,
                source_file,
                source_table,
                source_row,
                check_name,
                column_name,
                failure_case
            FROM audit.validation_failures
            WHERE load_id = 'load-rejected'
            """
        ).fetchdf()
        run = connection.execute(
            """
            SELECT status, source_row_count, valid_row_count, invalid_row_count
            FROM audit.ingestion_runs
            WHERE load_id = 'load-rejected'
            """
        ).fetchone()

        assert len(failures) == len(validation.failure_cases)
        assert set(failures["source_file"]) == {
            f"{table}.csv" for table in failures["source_table"]
        }
        assert run == (
            "succeeded",
            sum(len(getattr(dataset, table)) for table in SOURCE_TABLES),
            int(validation.summary["valid_rows"].sum()),
            int(validation.summary["invalid_rows"].sum()),
        )

        for failure in failures.dropna(subset=["source_row"]).itertuples():
            exists = connection.execute(
                f"""
                SELECT count(*)
                FROM bronze.{failure.source_table}
                WHERE _load_id = ? AND _source_row = ?
                """,
                [failure.load_id, failure.source_row],
            ).fetchone()
            assert exists == (1,)


def test_failed_ingestion_rolls_back_data_and_preserves_previous_run(
    tmp_path: Path,
) -> None:
    dataset = _dataset(error_rate=0.0)
    validation = validate_sources(dataset, load_id="load-failed")
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        connection.execute(
            """
            INSERT INTO audit.ingestion_runs VALUES (
                'load-previous',
                TIMESTAMP '2026-08-13 09:00:00',
                TIMESTAMP '2026-08-13 09:01:00',
                'succeeded',
                'previous-manifest',
                10,
                10,
                0,
                NULL
            )
            """
        )
        connection.execute("CREATE TABLE bronze.orders (wrong_column INTEGER)")

        with pytest.raises(duckdb.Error):
            ingest_to_bronze(dataset, validation, connection, load_id="load-failed")

        runs = connection.execute(
            """
            SELECT load_id, status, error_summary
            FROM audit.ingestion_runs
            ORDER BY load_id
            """
        ).fetchall()
        bronze_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'bronze'
                """
            ).fetchall()
        }

    assert runs[0][0:2] == ("load-failed", "failed")
    assert runs[0][2]
    assert runs[1] == ("load-previous", "succeeded", None)
    assert bronze_tables == {"orders"}


def test_ingestion_rejects_stale_validation_before_writing(
    tmp_path: Path,
) -> None:
    dataset = _dataset(error_rate=0.0)
    validation = validate_sources(dataset, load_id="load-stale")
    changed_products = dataset.products.copy()
    changed_products.loc[0, "base_price"] = -1.0
    changed_dataset = replace(dataset, products=changed_products)
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        with pytest.raises(ValueError, match="dataset manifest"):
            ingest_to_bronze(
                changed_dataset,
                validation,
                connection,
                load_id="load-stale",
            )
        run_count = connection.execute(
            "SELECT count(*) FROM audit.ingestion_runs"
        ).fetchone()
        bronze_count = connection.execute(
            """
            SELECT count(*)
            FROM information_schema.tables
            WHERE table_schema = 'bronze'
            """
        ).fetchone()

    assert run_count == (0,)
    assert bronze_count == (0,)


def test_ingestion_rejects_validation_for_another_load_id(
    tmp_path: Path,
) -> None:
    dataset = _dataset(error_rate=0.0)
    validation = validate_sources(dataset, load_id="load-validation")
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        with pytest.raises(ValueError, match="load_id"):
            ingest_to_bronze(
                dataset,
                validation,
                connection,
                load_id="load-other",
            )
