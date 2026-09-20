import streamlit as st

from src.data_workspace import (
    load_uploaded_files,
    profile_dataframe,
    run_read_only_query,
)


st.set_page_config(
    page_title="AI Data Insights",
    page_icon="📊",
    layout="wide",
)

st.title("AI Data Insights")
st.caption("Upload CSV or Excel files and explore them as SQL tables.")


if "tables" not in st.session_state:
    st.session_state.tables = {}

if "catalog" not in st.session_state:
    st.session_state.catalog = None

if "load_errors" not in st.session_state:
    st.session_state.load_errors = []


uploaded_files = st.file_uploader(
    "Upload one or more CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
)


if uploaded_files and st.button(
    "Process files",
    type="primary",
    use_container_width=True,
):
    with st.spinner("Reading and profiling files..."):
        tables, catalog, errors = load_uploaded_files(uploaded_files)

        st.session_state.tables = tables
        st.session_state.catalog = catalog
        st.session_state.load_errors = errors


for error in st.session_state.load_errors:
    st.warning(error)


tables = st.session_state.tables
catalog = st.session_state.catalog


if not tables:
    st.info("Upload files and click Process files to begin.")
    st.stop()


st.success(f"{len(tables)} table(s) loaded successfully.")


st.subheader("Data catalog")

if catalog is not None:
    st.dataframe(
        catalog,
        use_container_width=True,
        hide_index=True,
    )


selected_table = st.selectbox(
    "Select a table to inspect",
    options=list(tables.keys()),
)

selected_dataframe = tables[selected_table]


metric1, metric2, metric3 = st.columns(3)

metric1.metric("Rows", f"{len(selected_dataframe):,}")
metric2.metric("Columns", len(selected_dataframe.columns))
metric3.metric(
    "Missing cells",
    f"{int(selected_dataframe.isna().sum().sum()):,}",
)


preview_tab, profile_tab, statistics_tab = st.tabs(
    ["Preview", "Column profile", "Statistics"]
)


with preview_tab:
    st.dataframe(
        selected_dataframe.head(100),
        use_container_width=True,
    )


with profile_tab:
    profile = profile_dataframe(selected_dataframe)

    st.dataframe(
        profile,
        use_container_width=True,
        hide_index=True,
    )


with statistics_tab:
    try:
        statistics = selected_dataframe.describe(
            include="all"
        ).transpose()

        st.dataframe(
            statistics,
            use_container_width=True,
        )
    except Exception as error:
        st.warning(f"Statistics could not be generated: {error}")


st.divider()
st.subheader("Developer SQL test")

st.caption(
    "This verifies that DuckDB can query and join the uploaded tables."
)

default_query = f'SELECT * FROM "{selected_table}" LIMIT 10'

sql_query = st.text_area(
    "SQL query",
    value=default_query,
    height=150,
)


if st.button("Run SQL"):
    try:
        result = run_read_only_query(tables, sql_query)

        st.success(f"Query returned {len(result):,} row(s).")

        st.dataframe(
            result,
            use_container_width=True,
        )

    except Exception as error:
        st.error(f"Query failed: {error}")