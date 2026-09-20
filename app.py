import os

import pandas as pd
import streamlit as st
from datetime import datetime, timezone

from src.analysis_service import run_reliable_analysis
from src.data_workspace import (
    load_uploaded_files,
    profile_dataframe,
    run_read_only_query,
)

from src.insights import (
    build_kpis,
    build_summary,
    create_automatic_chart,
)

st.set_page_config(
    page_title="AI Data Insights",
    page_icon="📊",
    layout="wide",
)

def get_groq_api_key() -> str | None:
    try:
        return st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.getenv("GROQ_API_KEY")

st.title("AI Data Insights")
st.caption("Upload CSV or Excel files and explore them as SQL tables.")


if "ai_plan" not in st.session_state:
    st.session_state.ai_plan = None

if "ai_result" not in st.session_state:
    st.session_state.ai_result = None

if "ai_question" not in st.session_state:
    st.session_state.ai_question = ""

if "tables" not in st.session_state:
    st.session_state.tables = {}

if "catalog" not in st.session_state:
    st.session_state.catalog = None

if "load_errors" not in st.session_state:
    st.session_state.load_errors = []

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

if "last_execution" not in st.session_state:
    st.session_state.last_execution = None


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


#Phase 3

st.divider()
st.subheader("Ask your data")

st.caption(
    "Ask analytical questions using totals, averages, filters, "
    "comparisons, trends or cross-file joins."
)

question = st.text_input(
    "Enter your question",
    placeholder="Example: Which region generated the highest total sales?",
)

ask_button = st.button(
    "Generate and run analysis",
    type="primary",
    use_container_width=True,
)


if ask_button:
    api_key = get_groq_api_key()

    st.session_state.ai_plan = None
    st.session_state.ai_result = None
    st.session_state.ai_question = question
    st.session_state.last_execution = None

    if not api_key:
        st.error(
            "GROQ_API_KEY was not found. Add it to "
            ".streamlit/secrets.toml."
        )

    elif not question.strip():
        st.warning("Enter a question before running the analysis.")

    else:
        with st.spinner(
            "Generating, validating and executing the analysis..."
        ):
            outcome = run_reliable_analysis(
                api_key=api_key,
                question=question,
                tables=tables,
            )

        st.session_state.ai_plan = outcome["plan"]
        st.session_state.ai_result = outcome["result"]

        history_entry = {
            "timestamp": datetime.now(
                timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "question": question,
            "status": outcome["status"],
            "repair_used": outcome["repair_used"],
            "rows_returned": outcome["rows_returned"],
            "truncated": outcome["truncated"],
            "query_ms": outcome["query_execution_ms"],
            "total_ms": outcome["total_execution_ms"],
            "feedback": "",
        }

        st.session_state.analysis_history.append(history_entry)
        st.session_state.last_execution = history_entry

        if outcome["status"] == "success":
            if outcome["repair_used"]:
                st.warning(
                    "The first generated SQL failed. The application "
                    "repaired it once and successfully executed the "
                    "corrected query."
                )
            else:
                st.success(
                    "SQL validated and executed successfully."
                )

        elif outcome["status"] == "needs_clarification":
            clarification = outcome["plan"][
                "clarification_question"
            ]

            st.warning(clarification)

        else:
            st.error(
                "The analysis could not be completed safely. "
                f"Details: {outcome['error']}"
            )


plan = st.session_state.ai_plan
result = st.session_state.ai_result


if plan:
    if plan["status"] == "ready":
        st.write("**AI interpretation**")

        st.write(plan["explanation"])

        st.write("**Tables used**")

        st.write(", ".join(plan["tables_used"]))

        st.write("**Confidence**")

        st.progress(
            min(max(float(plan["confidence"]), 0.0), 1.0)
        )

        with st.expander("View generated SQL"):
            st.code(plan["sql"], language="sql")

    elif plan["status"] == "needs_clarification":
        st.info(
            "The AI needs more information before generating SQL."
        )


if isinstance(result, pd.DataFrame):
    st.divider()
    st.subheader("Analysis result")

    question_used = st.session_state.ai_question

    if result.empty:
        st.info(
            "The query ran successfully but returned no matching rows."
        )

    else:
        summary = build_summary(
            question=question_used,
            dataframe=result,
        )

        st.write("**Answer**")
        st.info(summary)

        kpis = build_kpis(result)

        if kpis:
            metric_columns = st.columns(len(kpis))

            for metric_column, (label, value) in zip(
                metric_columns,
                kpis,
            ):
                metric_column.metric(
                    label=label,
                    value=value,
                )

        figure, chart_reason = create_automatic_chart(
            question=question_used,
            dataframe=result,
        )

        if figure is not None:
            st.write("**Visual insight**")

            st.plotly_chart(
                figure,
                width="stretch",
                theme="streamlit",
            )

            st.caption(chart_reason)

            if len(result) > 30:
                st.caption(
                    "The chart shows the first 30 result rows "
                    "to remain readable."
                )

        else:
            st.caption(chart_reason)

        st.write("**Result data**")

        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = result.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download result as CSV",
            data=csv_data,
            file_name="analysis_result.csv",
            mime="text/csv",
        )


execution = st.session_state.last_execution

if execution:
    with st.expander("Execution details"):
        detail_columns = st.columns(4)

        detail_columns[0].metric(
            "Status",
            execution["status"].replace("_", " ").title(),
        )

        detail_columns[1].metric(
            "SQL Repair",
            "Used" if execution["repair_used"] else "Not needed",
        )

        detail_columns[2].metric(
            "Rows",
            f"{execution['rows_returned']:,}",
        )

        detail_columns[3].metric(
            "Query Time",
            f"{execution['query_ms']:,.2f} ms",
        )

        if execution["truncated"]:
            st.warning(
                "The result exceeded 1,000 rows and was truncated."
            )

if (
    execution
    and execution["status"] == "success"
    and st.session_state.analysis_history
):
    st.write("**Was this analysis correct?**")

    positive_column, negative_column = st.columns(2)

    current_history_index = (
        len(st.session_state.analysis_history) - 1
    )

    with positive_column:
        if st.button(
            "Correct",
            key=f"correct_{current_history_index}",
            use_container_width=True,
        ):
            st.session_state.analysis_history[
                current_history_index
            ]["feedback"] = "correct"

            st.success("Feedback recorded for this session.")

    with negative_column:
        if st.button(
            "Incorrect",
            key=f"incorrect_{current_history_index}",
            use_container_width=True,
        ):
            st.session_state.analysis_history[
                current_history_index
            ]["feedback"] = "incorrect"

            st.warning("Feedback recorded for this session.")

if st.session_state.analysis_history:
    with st.expander("Session analysis history"):
        history_dataframe = pd.DataFrame(
            st.session_state.analysis_history
        )

        st.dataframe(
            history_dataframe,
            use_container_width=True,
            hide_index=True,
        )