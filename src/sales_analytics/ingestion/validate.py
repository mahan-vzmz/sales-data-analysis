"""Validation adapter that turns Pandera failures into project reports."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import pandas as pd
import pandera.pandas as pa

from sales_analytics.ingestion.contracts import (
    SOURCE_TABLES,
    SourceDataset,
    build_source_schemas,
)

REPORT_COLUMNS = (
    "load_id",
    "source_table",
    "source_row",
    "check_name",
    "column_name",
    "failure_case",
)

CROSS_FIELD_COLUMNS = {
    "base_cost_lte_price": ("base_cost", "base_price"),
    "unit_cost_lte_unit_price": ("unit_cost", "unit_price"),
    "returned_quantity_lte_ordered": ("returned_quantity", "line_id"),
    "return_date_on_or_after_order": ("return_date", "line_id"),
    "promotion_start_lte_end": ("start_date", "end_date"),
}


@dataclass(frozen=True)
class ValidationResult:
    """Accepted row candidates and all source-contract findings."""

    load_id: str
    source_manifest_hash: str
    valid_candidates: dict[str, pd.DataFrame]
    failure_cases: pd.DataFrame
    summary: pd.DataFrame


def validate_sources(dataset: SourceDataset, load_id: str) -> ValidationResult:
    """Validate every source lazily and aggregate all failures."""
    schemas = build_source_schemas(dataset)
    reports: list[pd.DataFrame] = []
    valid_candidates: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict[str, object]] = []

    for source_table, schema in schemas.items():
        source = getattr(dataset, source_table)
        try:
            schema.validate(source, lazy=True)
            table_report = _empty_report()
        except pa.errors.SchemaErrors as error:
            table_report = _adapt_failures(
                error.failure_cases, schema, load_id, source_table
            )

        reports.append(table_report)
        invalid_rows = {row for row in table_report["source_row"] if pd.notna(row)}
        has_table_failure = table_report["source_row"].isna().any()
        valid = (
            source.iloc[0:0].copy() if has_table_failure else source.drop(invalid_rows)
        )
        valid_candidates[source_table] = valid
        summary_rows.append(
            {
                "source_table": source_table,
                "total_rows": len(source),
                "valid_rows": len(valid),
                "invalid_rows": len(source) - len(valid),
                "failure_count": len(table_report),
            }
        )

    failure_cases = (
        pd.concat(reports, ignore_index=True) if reports else _empty_report()
    )
    return ValidationResult(
        load_id=load_id,
        source_manifest_hash=source_manifest_hash(dataset),
        valid_candidates=valid_candidates,
        failure_cases=failure_cases.loc[:, list(REPORT_COLUMNS)],
        summary=pd.DataFrame(summary_rows),
    )


def source_manifest_hash(dataset: SourceDataset) -> str:
    """Fingerprint all raw source content and structure for one dataset."""
    digest = sha256()
    for table in SOURCE_TABLES:
        source = getattr(dataset, table)
        digest.update(table.encode())
        digest.update("\x1f".join(map(str, source.columns)).encode())
        digest.update("\x1f".join(map(str, source.dtypes)).encode())
        row_hashes = pd.util.hash_pandas_object(source, index=True)
        digest.update(np.asarray(row_hashes, dtype=np.uint64).tobytes())
    return digest.hexdigest()


def _adapt_failures(
    failures: pd.DataFrame,
    schema: pa.DataFrameSchema,
    load_id: str,
    source_table: str,
) -> pd.DataFrame:
    failures = _collapse_cross_field_failures(failures)
    check_names = {
        (str(column_name), str(check.error)): check.name
        for column_name, column in schema.columns.items()
        for check in column.checks
        if check.error is not None and check.name is not None
    }
    normalized_checks = [
        check_names.get((str(column), str(check)), check)
        for column, check in zip(failures["column"], failures["check"], strict=True)
    ]
    column_names = [
        failure_case if check == "column_in_dataframe" else column
        for column, check, failure_case in zip(
            failures["column"],
            failures["check"],
            failures["failure_case"],
            strict=True,
        )
    ]
    return pd.DataFrame(
        {
            "load_id": load_id,
            "source_table": source_table,
            "source_row": failures["index"],
            "check_name": normalized_checks,
            "column_name": column_names,
            "failure_case": failures["failure_case"],
        }
    )


def _empty_report() -> pd.DataFrame:
    return pd.DataFrame(columns=REPORT_COLUMNS)


def _collapse_cross_field_failures(failures: pd.DataFrame) -> pd.DataFrame:
    cross_field = (
        failures["schema_context"].eq("DataFrameSchema") & failures["index"].notna()
    )
    if not cross_field.any():
        return failures

    collapsed: list[dict[str, object]] = []
    for (source_row, check), group in failures.loc[cross_field].groupby(
        ["index", "check"], dropna=False
    ):
        columns = CROSS_FIELD_COLUMNS.get(str(check), tuple(group["column"]))
        values = dict(zip(group["column"], group["failure_case"], strict=True))
        collapsed.append(
            {
                "schema_context": "DataFrameSchema",
                "column": ",".join(columns),
                "check": check,
                "check_number": group["check_number"].iloc[0],
                "failure_case": ", ".join(
                    f"{column}={values.get(column)!r}" for column in columns
                ),
                "index": source_row,
            }
        )

    return pd.concat(
        (
            failures.loc[~cross_field],
            pd.DataFrame(collapsed, columns=failures.columns),
        ),
        ignore_index=True,
    )
