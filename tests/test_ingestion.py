from io import BytesIO

import pandas as pd

from src.ingestion import (
    load_files,
    normalize_identifier,
)


def test_normalize_identifier():
    assert normalize_identifier(
        "Total Amount ₹",
        "column",
    ) == "total_amount"

    assert normalize_identifier(
        "2026 Sales",
        "column",
    ) == "field_2026_sales"


def test_load_csv_file():
    csv_content = (
        b"Order ID,Total Amount\n"
        b"1,100\n"
        b"2,200\n"
    )

    tables, errors = load_files(
        (
            (
                "Sales Report.csv",
                csv_content,
            ),
        )
    )

    assert not errors
    assert "sales_report" in tables

    dataframe = tables["sales_report"]["dataframe"]

    assert len(dataframe) == 2
    assert list(dataframe.columns) == [
        "order_id",
        "total_amount",
    ]


def test_load_multiple_excel_sheets():
    excel_buffer = BytesIO()

    first_sheet = pd.DataFrame(
        {
            "Customer ID": [1, 2],
            "Name": ["A", "B"],
        }
    )

    second_sheet = pd.DataFrame(
        {
            "Order ID": [101, 102],
            "Amount": [500, 700],
        }
    )

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl",
    ) as writer:
        first_sheet.to_excel(
            writer,
            sheet_name="Customers",
            index=False,
        )

        second_sheet.to_excel(
            writer,
            sheet_name="Orders",
            index=False,
        )

    tables, errors = load_files(
        (
            (
                "Business Data.xlsx",
                excel_buffer.getvalue(),
            ),
        )
    )

    assert not errors

    assert "business_data_customers" in tables
    assert "business_data_orders" in tables


def test_reject_unsupported_file():
    tables, errors = load_files(
        (
            (
                "document.pdf",
                b"not-a-real-pdf",
            ),
        )
    )

    assert not tables
    assert len(errors) == 1
    assert "Unsupported extension" in errors[0]["error"]