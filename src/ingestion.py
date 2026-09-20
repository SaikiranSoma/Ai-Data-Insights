from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class IngestionError(Exception):
    """Raised when an uploaded file cannot be processed."""


def normalize_identifier(value: object, fallback: str) -> str:
    """
    Convert a filename, sheet name, or column name into a safe identifier.

    Examples:
        "Order ID"       -> "order_id"
        "Total Amount ₹" -> "total_amount"
        "2026 Sales"     -> "field_2026_sales"
    """
    identifier = str(value).strip().lower()

    identifier = re.sub(
        pattern=r"[^a-z0-9_]+",
        repl="_",
        string=identifier,
    )

    identifier = re.sub(
        pattern=r"_+",
        repl="_",
        string=identifier,
    ).strip("_")

    if not identifier:
        identifier = fallback

    if identifier[0].isdigit():
        identifier = f"field_{identifier}"

    return identifier


def normalize_columns(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Normalize column names and make duplicate names unique.

    Returns:
        Normalized DataFrame
        Mapping between original and normalized column names
    """
    dataframe = dataframe.copy()

    normalized_columns: list[str] = []
    column_mapping: list[dict[str, Any]] = []
    name_counts: dict[str, int] = {}

    for position, original_column in enumerate(dataframe.columns):
        original_name = str(original_column)

        base_name = normalize_identifier(
            original_name,
            fallback=f"column_{position + 1}",
        )

        name_counts[base_name] = name_counts.get(base_name, 0) + 1
        occurrence = name_counts[base_name]

        if occurrence == 1:
            normalized_name = base_name
        else:
            normalized_name = f"{base_name}_{occurrence}"

        normalized_columns.append(normalized_name)

        column_mapping.append(
            {
                "position": position + 1,
                "original_name": original_name,
                "normalized_name": normalized_name,
            }
        )

    dataframe.columns = normalized_columns

    return dataframe, column_mapping


def read_csv_file(
    content: bytes,
) -> tuple[pd.DataFrame, str]:
    """
    Read a CSV file using common text encodings.

    It initially assumes comma-separated data. If only one column is
    detected, it attempts delimiter auto-detection.
    """
    encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            dataframe = pd.read_csv(
                BytesIO(content),
                encoding=encoding,
            )

            if len(dataframe.columns) == 1:
                try:
                    detected_dataframe = pd.read_csv(
                        BytesIO(content),
                        encoding=encoding,
                        sep=None,
                        engine="python",
                    )

                    if len(detected_dataframe.columns) > 1:
                        dataframe = detected_dataframe

                except (pd.errors.ParserError, UnicodeDecodeError):
                    pass

            return dataframe, encoding

        except UnicodeDecodeError as error:
            last_error = error

        except pd.errors.EmptyDataError as error:
            raise IngestionError("The CSV file is empty.") from error

        except pd.errors.ParserError as error:
            last_error = error

    raise IngestionError(
        f"The CSV file could not be parsed: {last_error}"
    )


def read_excel_file(
    content: bytes,
    extension: str,
) -> dict[str, pd.DataFrame]:
    """
    Read every sheet from an Excel workbook.
    """
    engine = "xlrd" if extension == ".xls" else "openpyxl"

    try:
        workbook = pd.ExcelFile(
            BytesIO(content),
            engine=engine,
        )

        if not workbook.sheet_names:
            raise IngestionError(
                "The Excel workbook does not contain any sheets."
            )

        return {
            sheet_name: workbook.parse(sheet_name=sheet_name)
            for sheet_name in workbook.sheet_names
        }

    except IngestionError:
        raise

    except Exception as error:
        raise IngestionError(
            f"The Excel workbook could not be read: {error}"
        ) from error


def create_unique_name(
    requested_name: str,
    existing_names: set[str],
) -> str:
    """
    Prevent tables from overwriting one another when names collide.
    """
    if requested_name not in existing_names:
        return requested_name

    suffix = 2

    while f"{requested_name}_{suffix}" in existing_names:
        suffix += 1

    return f"{requested_name}_{suffix}"


def load_single_file(
    filename: str,
    content: bytes,
) -> list[dict[str, Any]]:
    """
    Convert one CSV or Excel file into one or more table records.

    A CSV creates one table.
    Every Excel sheet creates a separate table.
    """
    safe_filename = Path(filename).name
    extension = Path(safe_filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise IngestionError(
            f"Unsupported extension '{extension}'. "
            "Only CSV, XLSX and XLS files are supported."
        )

    if not content:
        raise IngestionError("The uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise IngestionError(
            f"The file exceeds the {MAX_FILE_SIZE_MB} MB limit."
        )

    file_stem = normalize_identifier(
        Path(safe_filename).stem,
        fallback="table",
    )

    loaded_tables: list[dict[str, Any]] = []

    if extension == ".csv":
        dataframe, encoding = read_csv_file(content)

        dataframe, column_mapping = normalize_columns(dataframe)

        loaded_tables.append(
            {
                "table_name": file_stem,
                "source_file": safe_filename,
                "sheet_name": None,
                "encoding": encoding,
                "dataframe": dataframe,
                "column_mapping": column_mapping,
            }
        )

        return loaded_tables

    excel_sheets = read_excel_file(content, extension)

    for sheet_name, dataframe in excel_sheets.items():
        normalized_sheet_name = normalize_identifier(
            sheet_name,
            fallback="sheet",
        )

        table_name = f"{file_stem}_{normalized_sheet_name}"

        dataframe, column_mapping = normalize_columns(dataframe)

        loaded_tables.append(
            {
                "table_name": table_name,
                "source_file": safe_filename,
                "sheet_name": sheet_name,
                "encoding": None,
                "dataframe": dataframe,
                "column_mapping": column_mapping,
            }
        )

    return loaded_tables


def load_files(
    files: tuple[tuple[str, bytes], ...],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    """
    Process all uploaded files.

    Returns:
        Dictionary of successfully loaded tables
        List of file-level errors
    """
    tables: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []

    for filename, content in files:
        try:
            loaded_tables = load_single_file(
                filename=filename,
                content=content,
            )

            for table_record in loaded_tables:
                unique_name = create_unique_name(
                    requested_name=table_record["table_name"],
                    existing_names=set(tables.keys()),
                )

                table_record["table_name"] = unique_name
                tables[unique_name] = table_record

        except IngestionError as error:
            errors.append(
                {
                    "file": filename,
                    "error": str(error),
                }
            )

        except Exception as error:
            errors.append(
                {
                    "file": filename,
                    "error": f"Unexpected error: {error}",
                }
            )

    return tables, errors


def build_column_profile(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produce schema and data-quality information for each column.
    """
    profile_rows: list[dict[str, Any]] = []
    row_count = len(dataframe)

    for column_name in dataframe.columns:
        series = dataframe[column_name]

        null_count = int(series.isna().sum())
        non_null_count = int(series.notna().sum())

        try:
            unique_count = int(series.nunique(dropna=True))
        except TypeError:
            unique_count = 0

        null_percentage = (
            round((null_count / row_count) * 100, 2)
            if row_count
            else 0.0
        )

        profile_rows.append(
            {
                "column": column_name,
                "data_type": str(series.dtype),
                "non_null_values": non_null_count,
                "null_values": null_count,
                "null_percentage": null_percentage,
                "unique_values": unique_count,
            }
        )

    return pd.DataFrame(profile_rows)


def dataframe_memory_mb(dataframe: pd.DataFrame) -> float:
    """
    Estimate DataFrame memory consumption in megabytes.
    """
    memory_bytes = dataframe.memory_usage(
        index=True,
        deep=True,
    ).sum()

    return round(memory_bytes / (1024 * 1024), 2)