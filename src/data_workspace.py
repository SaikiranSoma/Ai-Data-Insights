from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import threading
import time


def clean_table_name(name: str) -> str:
    """Convert a filename or sheet name into a safe SQL table name."""

    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", name)
    cleaned = cleaned.strip("_").lower()

    if not cleaned:
        cleaned = "table"

    if cleaned[0].isdigit():
        cleaned = f"table_{cleaned}"

    return cleaned

def unique_table_name(base_name: str, existing_names: set[str]) -> str:
    """Prevent tables from overwriting each other."""

    name = base_name
    counter = 2

    while name in existing_names:
        name = f"{base_name}_{counter}"
        counter += 1

    return name


def read_csv_file(file_bytes: bytes) -> pd.DataFrame:
    """Read CSV files using common encodings."""

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            return pd.read_csv(BytesIO(file_bytes), encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error

    raise ValueError("Could not determine the CSV file encoding.") from last_error


def load_uploaded_files(
    uploaded_files: list[Any],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, list[str]]:
    """
    Convert uploaded CSV and Excel files into named Pandas DataFrames.

    Returns:
        tables: SQL table name mapped to DataFrame
        catalog: Summary of loaded tables
        errors: Files or sheets that could not be loaded
    """

    tables: dict[str, pd.DataFrame] = {}
    catalog_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        extension = Path(filename).suffix.lower()
        file_stem = clean_table_name(Path(filename).stem)
        file_bytes = uploaded_file.getvalue()

        try:
            if extension == ".csv":
                dataframe = read_csv_file(file_bytes)

                table_name = unique_table_name(
                    file_stem,
                    set(tables.keys()),
                )

                tables[table_name] = dataframe

                catalog_rows.append(
                    {
                        "table_name": table_name,
                        "source_file": filename,
                        "sheet_name": None,
                        "rows": len(dataframe),
                        "columns": len(dataframe.columns),
                    }
                )

            elif extension in {".xlsx", ".xls"}:
                sheets = pd.read_excel(
                    BytesIO(file_bytes),
                    sheet_name=None,
                )

                for sheet_name, dataframe in sheets.items():
                    if dataframe.empty:
                        continue

                    base_name = clean_table_name(
                        f"{file_stem}_{sheet_name}"
                    )

                    table_name = unique_table_name(
                        base_name,
                        set(tables.keys()),
                    )

                    tables[table_name] = dataframe

                    catalog_rows.append(
                        {
                            "table_name": table_name,
                            "source_file": filename,
                            "sheet_name": sheet_name,
                            "rows": len(dataframe),
                            "columns": len(dataframe.columns),
                        }
                    )

            else:
                errors.append(f"{filename}: unsupported file type")

        except Exception as error:
            errors.append(f"{filename}: {error}")

    catalog = pd.DataFrame(catalog_rows)

    return tables, catalog, errors


def profile_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Create a column-level profile for a DataFrame."""

    profile_rows: list[dict[str, Any]] = []

    for column in dataframe.columns:
        series = dataframe[column]
        non_null_values = series.dropna()

        examples = [
            str(value)[:50]
            for value in non_null_values.head(3).tolist()
        ]

        profile_rows.append(
            {
                "column": str(column),
                "data_type": str(series.dtype),
                "non_null_count": int(series.notna().sum()),
                "missing_count": int(series.isna().sum()),
                "missing_percent": round(
                    float(series.isna().mean() * 100),
                    2,
                ),
                "unique_values": int(series.nunique(dropna=True)),
                "examples": ", ".join(examples),
            }
        )

    return pd.DataFrame(profile_rows)


def validate_read_only_query(query: str) -> str:
    """Validate and normalize SQL before execution."""

    normalized_query = query.strip()
    cleaned_query = normalized_query.rstrip(";").strip()

    if not cleaned_query:
        raise ValueError("SQL query cannot be empty.")

    if len(cleaned_query) > 20_000:
        raise ValueError("SQL query is unexpectedly long.")

    if not cleaned_query.lower().startswith(("select", "with")):
        raise ValueError(
            "Only SELECT statements and WITH queries are allowed."
        )

    if ";" in cleaned_query:
        raise ValueError(
            "Multiple SQL statements are not allowed."
        )

    forbidden_keywords = re.compile(
        r"\b("
        r"insert|update|delete|drop|alter|create|replace|"
        r"copy|attach|detach|install|load|export|import|"
        r"pragma|call|vacuum|truncate|grant|revoke|set|reset"
        r")\b",
        re.IGNORECASE,
    )

    if forbidden_keywords.search(cleaned_query):
        raise ValueError(
            "The SQL contains a forbidden operation."
        )

    return cleaned_query


def run_read_only_query(
    tables: dict[str, pd.DataFrame],
    query: str,
    max_rows: int = 1_000,
    timeout_seconds: float = 8.0,
) -> pd.DataFrame:
    """
    Execute guarded read-only SQL.

    Protections:
        Read-only validation
        External access disabled
        Query timeout
        Maximum result size
        DuckDB syntax and binding validation
    """

    cleaned_query = validate_read_only_query(query)

    if max_rows < 1:
        raise ValueError("max_rows must be at least 1.")

    connection = duckdb.connect(
        database=":memory:",
        config={"enable_external_access": "false"},
    )

    timed_out = threading.Event()
    timeout_timer: threading.Timer | None = None
    started_at = time.perf_counter()

    def interrupt_query() -> None:
        timed_out.set()
        connection.interrupt()

    try:
        for table_name, dataframe in tables.items():
            connection.register(table_name, dataframe)

        # Validate syntax, tables and columns before execution.
        connection.execute(f"EXPLAIN {cleaned_query}")

        limited_query = (
            "SELECT * FROM ("
            f"{cleaned_query}"
            ") AS guarded_result "
            f"LIMIT {max_rows + 1}"
        )

        if timeout_seconds > 0:
            timeout_timer = threading.Timer(
                timeout_seconds,
                interrupt_query,
            )
            timeout_timer.daemon = True
            timeout_timer.start()

        result = connection.execute(limited_query).df()

        was_truncated = len(result) > max_rows

        if was_truncated:
            result = result.iloc[:max_rows].copy()

        execution_ms = round(
            (time.perf_counter() - started_at) * 1_000,
            2,
        )

        result.attrs["truncated"] = was_truncated
        result.attrs["execution_ms"] = execution_ms
        result.attrs["row_limit"] = max_rows

        return result

    except Exception as error:
        if timed_out.is_set():
            raise TimeoutError(
                f"Query exceeded the {timeout_seconds}-second limit."
            ) from error

        raise

    finally:
        if timeout_timer is not None:
            timeout_timer.cancel()

        connection.close()