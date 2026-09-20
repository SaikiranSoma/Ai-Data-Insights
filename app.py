from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ingestion import (
    MAX_FILE_SIZE_MB,
    build_column_profile,
    dataframe_memory_mb,
    load_files,
)


MAX_FILES = 10
DEFAULT_PREVIEW_ROWS = 20


st.set_page_config(
    page_title="AI Data Insights",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def cached_load_files(
    file_payloads: tuple[tuple[str, bytes], ...],
):
    """
    Cache parsing results so files are not repeatedly processed
    during Streamlit reruns.
    """
    return load_files(file_payloads)


@st.cache_data(show_spinner=False)
def cached_column_profile(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cache column profiling because unique-value calculations
    can be relatively expensive.
    """
    return build_column_profile(dataframe)


def build_table_summary(
    tables: dict,
) -> pd.DataFrame:
    """
    Build a summary table covering all uploaded datasets.
    """
    summary_rows = []

    for table_name, table_record in tables.items():
        dataframe = table_record["dataframe"]

        summary_rows.append(
            {
                "table": table_name,
                "source_file": table_record["source_file"],
                "sheet": table_record["sheet_name"] or "CSV",
                "rows": len(dataframe),
                "columns": len(dataframe.columns),
                "memory_mb": dataframe_memory_mb(dataframe),
            }
        )

    return pd.DataFrame(summary_rows)


def initialize_session_state() -> None:
    if "loaded_tables" not in st.session_state:
        st.session_state.loaded_tables = {}

    if "ingestion_errors" not in st.session_state:
        st.session_state.ingestion_errors = []


initialize_session_state()


st.title("AI Data Insights")

st.write(
    "Upload multiple CSV or Excel files to inspect their tables, "
    "schemas and data quality."
)

st.caption(
    "Phase 1 handles file validation and ingestion. "
    "Analysis and AI-generated queries will be added in later phases."
)


with st.sidebar:
    st.header("Upload data")

    uploaded_files = st.file_uploader(
        label="Select CSV or Excel files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help=(
            f"Maximum {MAX_FILES} files. "
            f"Maximum {MAX_FILE_SIZE_MB} MB per file."
        ),
    )

    process_files = st.button(
        "Load and inspect files",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files,
    )

    st.caption(
        "Supported formats: CSV, XLSX and XLS."
    )


if process_files:
    if len(uploaded_files) > MAX_FILES:
        st.error(
            f"You selected {len(uploaded_files)} files. "
            f"The maximum is {MAX_FILES}."
        )
    else:
        file_payloads = tuple(
            (
                uploaded_file.name,
                uploaded_file.getvalue(),
            )
            for uploaded_file in uploaded_files
        )

        with st.spinner("Validating and loading files..."):
            tables, errors = cached_load_files(file_payloads)

        st.session_state.loaded_tables = tables
        st.session_state.ingestion_errors = errors


for ingestion_error in st.session_state.ingestion_errors:
    st.warning(
        f"{ingestion_error['file']}: "
        f"{ingestion_error['error']}"
    )


tables = st.session_state.loaded_tables

if not tables:
    st.info(
        "Upload one or more files and select "
        "'Load and inspect files' to begin."
    )

    st.stop()


table_summary = build_table_summary(tables)

total_rows = sum(
    len(table_record["dataframe"])
    for table_record in tables.values()
)

total_columns = sum(
    len(table_record["dataframe"].columns)
    for table_record in tables.values()
)


metric_column_1, metric_column_2, metric_column_3 = st.columns(3)

metric_column_1.metric(
    label="Detected tables",
    value=len(tables),
)

metric_column_2.metric(
    label="Total rows",
    value=f"{total_rows:,}",
)

metric_column_3.metric(
    label="Total columns",
    value=f"{total_columns:,}",
)


st.subheader("Uploaded data summary")

st.dataframe(
    table_summary,
    use_container_width=True,
    hide_index=True,
)


st.subheader("Inspect a table")

selected_table_name = st.selectbox(
    label="Select a detected table",
    options=list(tables.keys()),
)

preview_row_count = st.slider(
    label="Preview rows",
    min_value=5,
    max_value=100,
    value=DEFAULT_PREVIEW_ROWS,
    step=5,
)


selected_record = tables[selected_table_name]
selected_dataframe = selected_record["dataframe"]


source_details = (
    f"Source file: {selected_record['source_file']}"
)

if selected_record["sheet_name"]:
    source_details += (
        f" | Excel sheet: {selected_record['sheet_name']}"
    )

if selected_record["encoding"]:
    source_details += (
        f" | Encoding: {selected_record['encoding']}"
    )

st.caption(source_details)


detail_column_1, detail_column_2, detail_column_3 = st.columns(3)

detail_column_1.metric(
    label="Rows",
    value=f"{len(selected_dataframe):,}",
)

detail_column_2.metric(
    label="Columns",
    value=len(selected_dataframe.columns),
)

detail_column_3.metric(
    label="Memory",
    value=f"{dataframe_memory_mb(selected_dataframe)} MB",
)


st.markdown("#### Data preview")

st.dataframe(
    selected_dataframe.head(preview_row_count),
    use_container_width=True,
    hide_index=True,
)


st.markdown("#### Column profile")

column_profile = cached_column_profile(
    selected_dataframe
)

st.dataframe(
    column_profile,
    use_container_width=True,
    hide_index=True,
)


column_mapping = pd.DataFrame(
    selected_record["column_mapping"]
)

columns_were_changed = any(
    row["original_name"] != row["normalized_name"]
    for row in selected_record["column_mapping"]
)

with st.expander(
    "View original and normalized column names",
    expanded=columns_were_changed,
):
    st.dataframe(
        column_mapping,
        use_container_width=True,
        hide_index=True,
    )