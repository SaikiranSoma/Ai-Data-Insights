import pandas as pd
import pytest

from src.data_workspace import run_read_only_query


@pytest.fixture
def tables():
    return {
        "orders": pd.DataFrame(
            {
                "order_id": [1, 2, 3, 4, 5],
                "region": [
                    "North",
                    "South",
                    "North",
                    "West",
                    "South",
                ],
                "amount": [100, 200, 150, 300, 250],
            }
        )
    }


def test_select_query_works(tables):
    result = run_read_only_query(
        tables,
        """
        SELECT region, SUM(amount) AS total_amount
        FROM orders
        GROUP BY region
        ORDER BY total_amount DESC
        """,
    )

    assert not result.empty
    assert "total_amount" in result.columns


def test_delete_is_rejected(tables):
    with pytest.raises(ValueError):
        run_read_only_query(
            tables,
            "DELETE FROM orders",
        )


def test_drop_is_rejected(tables):
    with pytest.raises(ValueError):
        run_read_only_query(
            tables,
            "DROP TABLE orders",
        )


def test_multiple_statements_are_rejected(tables):
    with pytest.raises(ValueError):
        run_read_only_query(
            tables,
            "SELECT * FROM orders; SELECT 1",
        )


def test_unknown_table_is_rejected(tables):
    with pytest.raises(Exception):
        run_read_only_query(
            tables,
            "SELECT * FROM nonexistent_table",
        )


def test_external_file_access_is_rejected(tables):
    with pytest.raises(Exception):
        run_read_only_query(
            tables,
            """
            SELECT *
            FROM read_csv_auto('private_file.csv')
            """,
        )


def test_result_is_limited(tables):
    result = run_read_only_query(
        tables,
        "SELECT * FROM orders",
        max_rows=3,
    )

    assert len(result) == 3
    assert result.attrs["truncated"] is True


def test_aggregation_is_correct(tables):
    result = run_read_only_query(
        tables,
        """
        SELECT SUM(amount) AS total_amount
        FROM orders
        """,
    )

    assert result.iloc[0]["total_amount"] == 1000