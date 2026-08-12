"""Excel exports for the legacy v1 pipeline."""

from pathlib import Path

import pandas as pd


def export_cleaned_workbook(
    clean_df: pd.DataFrame,
    cleaning_log: pd.DataFrame,
    path: Path,
) -> None:
    """Persist the cleaned dataset and its audit log."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        clean_df.to_excel(writer, sheet_name="Cleaned_Data", index=False)
        cleaning_log.to_excel(writer, sheet_name="Cleaning_Log", index=False)


def export_report(
    analysis_df: pd.DataFrame,
    analyses: dict[str, pd.DataFrame],
    path: Path,
) -> None:
    """Write the KPI summary and grouped analysis tables."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        analyses["Summary"].to_excel(writer, sheet_name="Summary", index=False)
        analysis_df.to_excel(writer, sheet_name="Cleaned_Data", index=False)

        for sheet_name in [
            "Monthly_Sales",
            "Product_Analysis",
            "Category_Analysis",
            "City_Analysis",
            "Payment_Analysis",
        ]:
            analyses[sheet_name].to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
            )
