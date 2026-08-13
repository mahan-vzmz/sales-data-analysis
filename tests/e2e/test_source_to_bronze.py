from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb

from sales_analytics.generation.generator import GeneratorConfig, generate_dataset
from sales_analytics.ingestion.bronze import (
    SOURCE_TABLES,
    bootstrap_warehouse,
    ingest_to_bronze,
)
from sales_analytics.ingestion.validate import validate_sources

PROJECT_ROOT = Path(__file__).parents[2]


def test_generated_source_to_bronze_is_idempotent(tmp_path: Path) -> None:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    config = replace(
        configured,
        customer_count=10,
        error_rates={name: 0.01 for name in configured.error_rates},
    )
    dataset = generate_dataset(config)
    validation = validate_sources(dataset, load_id="load-first")
    repeated_validation = validate_sources(dataset, load_id="load-repeat")
    warehouse_path = tmp_path / "warehouse" / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        first = ingest_to_bronze(dataset, validation, connection, load_id="load-first")
        repeated = ingest_to_bronze(
            dataset, repeated_validation, connection, load_id="load-repeat"
        )

        audit_run_count = connection.execute(
            "SELECT count(*) FROM audit.ingestion_runs"
        ).fetchone()
        failure_count = connection.execute(
            "SELECT count(*) FROM audit.validation_failures"
        ).fetchone()
        bronze_counts = {
            table: connection.execute(
                f"SELECT count(*) FROM bronze.{table}"
            ).fetchone()[0]
            for table in SOURCE_TABLES
        }

    assert first.status == "succeeded"
    assert repeated.status == "skipped"
    assert repeated.source_manifest_hash == first.source_manifest_hash
    assert audit_run_count == (1,)
    assert failure_count == (len(validation.failure_cases),)
    assert bronze_counts == {
        table: len(getattr(dataset, table)) for table in SOURCE_TABLES
    }


def test_empty_returns_batch_accepts_later_return_rows(tmp_path: Path) -> None:
    configured = GeneratorConfig.from_json(
        PROJECT_ROOT / "data" / "fixtures" / "generator_config.json"
    )
    clean_config = replace(
        configured,
        customer_count=10,
        error_rates={name: 0.0 for name in configured.error_rates},
    )
    no_returns_config = replace(
        clean_config,
        patterns=replace(clean_config.patterns, return_probability=0.0),
    )
    no_returns = generate_dataset(no_returns_config)
    with_returns = generate_dataset(clean_config)
    warehouse_path = tmp_path / "sales.duckdb"
    bootstrap_warehouse(warehouse_path)

    with duckdb.connect(str(warehouse_path)) as connection:
        first = ingest_to_bronze(
            no_returns,
            validate_sources(no_returns, load_id="load-empty-returns"),
            connection,
            load_id="load-empty-returns",
        )
        second = ingest_to_bronze(
            with_returns,
            validate_sources(with_returns, load_id="load-with-returns"),
            connection,
            load_id="load-with-returns",
        )
        stored_returns = connection.execute(
            "SELECT count(*) FROM bronze.returns"
        ).fetchone()

    assert no_returns.returns.empty
    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert stored_returns == (len(with_returns.returns),)
