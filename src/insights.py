from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure


DATE_HINTS = {
    "date",
    "time",
    "day",
    "week",
    "month",
    "quarter",
    "year",
}

IDENTIFIER_HINTS = {
    "id",
    "customer_id",
    "order_id",
    "product_id",
    "employee_id",
}

SHARE_KEYWORDS = {
    "share",
    "percentage",
    "proportion",
    "contribution",
}

RELATIONSHIP_KEYWORDS = {
    "relationship",
    "correlation",
    "compare",
    "scatter",
}

DISTRIBUTION_KEYWORDS = {
    "distribution",
    "histogram",
    "spread",
    "frequency",
}


def readable_name(column_name: str) -> str:
    """Convert column_name into Column Name."""

    return column_name.replace("_", " ").strip().title()


def format_value(value: Any) -> str:
    """Format values for summaries and KPI cards."""

    if pd.isna(value):
        return "N/A"

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, int):
        return f"{value:,}"

    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    return str(value)


def is_identifier(column_name: str) -> bool:
    normalized = column_name.lower()

    return (
        normalized in IDENTIFIER_HINTS
        or normalized.endswith("_id")
        or normalized == "id"
    )


def prepare_columns(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str], list[str]]:
    """
    Identify date, measure and category columns.

    Returns:
        prepared DataFrame
        date columns
        numeric measure columns
        category columns
    """

    prepared = dataframe.copy()

    date_columns: list[str] = []
    numeric_columns: list[str] = []
    category_columns: list[str] = []

    for column in prepared.columns:
        column_name = str(column)
        series = prepared[column]

        if pd.api.types.is_datetime64_any_dtype(series):
            date_columns.append(column_name)
            continue

        has_date_hint = any(
            hint in column_name.lower()
            for hint in DATE_HINTS
        )

        if has_date_hint and not pd.api.types.is_numeric_dtype(series):
            converted = pd.to_datetime(series, errors="coerce")
            valid_ratio = converted.notna().mean()

            if valid_ratio >= 0.8:
                prepared[column] = converted
                date_columns.append(column_name)
                continue

        if (
            pd.api.types.is_numeric_dtype(series)
            and not is_identifier(column_name)
        ):
            numeric_columns.append(column_name)
        else:
            category_columns.append(column_name)

    return (
        prepared,
        date_columns,
        numeric_columns,
        category_columns,
    )


def build_summary(
    question: str,
    dataframe: pd.DataFrame,
) -> str:
    """Generate a factual summary directly from the query result."""

    if dataframe.empty:
        return "The analysis completed successfully but found no matching records."

    prepared, date_columns, numeric_columns, category_columns = (
        prepare_columns(dataframe)
    )

    if len(prepared) == 1:
        values = []

        for column in prepared.columns[:4]:
            label = readable_name(str(column))
            value = format_value(prepared.iloc[0][column])
            values.append(f"{label}: {value}")

        return ". ".join(values) + "."

    if date_columns and numeric_columns:
        date_column = date_columns[0]
        value_column = numeric_columns[0]

        ordered = prepared[
            [date_column, value_column]
        ].dropna().sort_values(date_column)

        if len(ordered) >= 2:
            first_value = float(ordered.iloc[0][value_column])
            last_value = float(ordered.iloc[-1][value_column])
            difference = last_value - first_value

            if first_value != 0:
                percentage_change = difference / abs(first_value) * 100
                direction = (
                    "increased"
                    if percentage_change > 0
                    else "decreased"
                )

                return (
                    f"{readable_name(value_column)} {direction} from "
                    f"{format_value(first_value)} to "
                    f"{format_value(last_value)}, a change of "
                    f"{abs(percentage_change):.2f}% across the "
                    f"returned period."
                )

            return (
                f"{readable_name(value_column)} changed from "
                f"{format_value(first_value)} to "
                f"{format_value(last_value)} across the returned period."
            )

    if category_columns and numeric_columns:
        category_column = category_columns[0]
        value_column = numeric_columns[0]

        valid_rows = prepared[
            [category_column, value_column]
        ].dropna()

        if not valid_rows.empty:
            highest_index = valid_rows[value_column].idxmax()
            highest_row = valid_rows.loc[highest_index]

            return (
                f"The highest {readable_name(value_column).lower()} is "
                f"{format_value(highest_row[value_column])} for "
                f"{readable_name(category_column).lower()} "
                f"'{highest_row[category_column]}'. "
                f"The query returned {len(prepared):,} grouped rows."
            )

    return (
        f"The analysis returned {len(prepared):,} rows across "
        f"{len(prepared.columns):,} columns."
    )


def build_kpis(
    dataframe: pd.DataFrame,
) -> list[tuple[str, str]]:
    """Create KPI labels and values from the result."""

    if dataframe.empty:
        return []

    prepared, _, numeric_columns, category_columns = prepare_columns(
        dataframe
    )

    if len(prepared) == 1:
        return [
            (
                readable_name(str(column)),
                format_value(prepared.iloc[0][column]),
            )
            for column in prepared.columns[:4]
        ]

    kpis: list[tuple[str, str]] = [
        ("Rows Returned", f"{len(prepared):,}"),
        ("Result Columns", f"{len(prepared.columns):,}"),
    ]

    if numeric_columns:
        value_column = numeric_columns[0]
        maximum_value = prepared[value_column].max()

        kpis.append(
            (
                f"Highest {readable_name(value_column)}",
                format_value(maximum_value),
            )
        )

    if category_columns:
        category_column = category_columns[0]

        kpis.append(
            (
                f"Unique {readable_name(category_column)}",
                f"{prepared[category_column].nunique(dropna=True):,}",
            )
        )

    return kpis[:4]


def create_automatic_chart(
    question: str,
    dataframe: pd.DataFrame,
) -> tuple[Figure | None, str]:
    """
    Select and create a chart using deterministic rules.

    Returns:
        Plotly figure or None
        Explanation of the chart decision
    """

    if dataframe.empty:
        return None, "No chart was created because the result is empty."

    if len(dataframe) == 1:
        return None, "A single-row result is better displayed as KPI cards."

    prepared, date_columns, numeric_columns, category_columns = (
        prepare_columns(dataframe)
    )

    question_lower = question.lower()
    chart_data = prepared.head(30).copy()

    if date_columns and numeric_columns:
        x_column = date_columns[0]
        y_column = numeric_columns[0]

        chart_data = chart_data.sort_values(x_column)

        figure = px.line(
            chart_data,
            x=x_column,
            y=y_column,
            markers=True,
            title=(
                f"{readable_name(y_column)} by "
                f"{readable_name(x_column)}"
            ),
        )

        return figure, "Line chart selected for time-based data."

    if category_columns and numeric_columns:
        x_column = category_columns[0]
        y_column = numeric_columns[0]

        wants_share_chart = any(
            keyword in question_lower
            for keyword in SHARE_KEYWORDS
        )

        if wants_share_chart and len(chart_data) <= 8:
            figure = px.pie(
                chart_data,
                names=x_column,
                values=y_column,
                title=(
                    f"{readable_name(y_column)} Share by "
                    f"{readable_name(x_column)}"
                ),
            )

            return figure, "Pie chart selected for proportional data."

        figure = px.bar(
            chart_data,
            x=x_column,
            y=y_column,
            title=(
                f"{readable_name(y_column)} by "
                f"{readable_name(x_column)}"
            ),
            text_auto=".3s",
        )

        figure.update_layout(
            xaxis_title=readable_name(x_column),
            yaxis_title=readable_name(y_column),
        )

        return figure, "Bar chart selected for category comparison."

    wants_relationship_chart = any(
        keyword in question_lower
        for keyword in RELATIONSHIP_KEYWORDS
    )

    if len(numeric_columns) >= 2 and wants_relationship_chart:
        x_column = numeric_columns[0]
        y_column = numeric_columns[1]

        figure = px.scatter(
            chart_data,
            x=x_column,
            y=y_column,
            title=(
                f"{readable_name(y_column)} vs "
                f"{readable_name(x_column)}"
            ),
        )

        return figure, "Scatter chart selected for numeric comparison."

    wants_distribution_chart = any(
        keyword in question_lower
        for keyword in DISTRIBUTION_KEYWORDS
    )

    if numeric_columns and wants_distribution_chart:
        value_column = numeric_columns[0]

        figure = px.histogram(
            chart_data,
            x=value_column,
            title=f"Distribution of {readable_name(value_column)}",
        )

        return figure, "Histogram selected for numeric distribution."

    return (
        None,
        "No chart was generated because the result does not have "
        "a clearly suitable visual structure.",
    )