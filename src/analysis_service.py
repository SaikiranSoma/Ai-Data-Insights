from __future__ import annotations

from time import perf_counter
from typing import Any

import pandas as pd

from src.ai_sql import (
    generate_sql_plan,
    repair_sql_plan,
)
from src.data_workspace import run_read_only_query


def run_reliable_analysis(
    api_key: str,
    question: str,
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """
    Run natural-language analysis with one optional repair attempt.
    """

    started_at = perf_counter()

    outcome: dict[str, Any] = {
        "status": "failed",
        "plan": None,
        "result": None,
        "repair_used": False,
        "original_sql": "",
        "final_sql": "",
        "error": "",
        "total_execution_ms": 0.0,
        "query_execution_ms": 0.0,
        "rows_returned": 0,
        "truncated": False,
    }

    try:
        initial_plan = generate_sql_plan(
            api_key=api_key,
            question=question,
            tables=tables,
        )

        outcome["plan"] = initial_plan
        outcome["original_sql"] = initial_plan.get("sql", "")

        if initial_plan["status"] == "needs_clarification":
            outcome["status"] = "needs_clarification"
            return outcome

        try:
            result = run_read_only_query(
                tables=tables,
                query=initial_plan["sql"],
                max_rows=1_000,
                timeout_seconds=8.0,
            )

            final_plan = initial_plan

        except Exception as first_error:
            outcome["repair_used"] = True

            repaired_plan = repair_sql_plan(
                api_key=api_key,
                question=question,
                tables=tables,
                failed_plan=initial_plan,
                database_error=str(first_error),
            )

            outcome["plan"] = repaired_plan

            if repaired_plan["status"] == "needs_clarification":
                outcome["status"] = "needs_clarification"
                return outcome

            result = run_read_only_query(
                tables=tables,
                query=repaired_plan["sql"],
                max_rows=1_000,
                timeout_seconds=8.0,
            )

            final_plan = repaired_plan

        outcome["status"] = "success"
        outcome["plan"] = final_plan
        outcome["result"] = result
        outcome["final_sql"] = final_plan["sql"]
        outcome["rows_returned"] = len(result)
        outcome["truncated"] = bool(
            result.attrs.get("truncated", False)
        )
        outcome["query_execution_ms"] = float(
            result.attrs.get("execution_ms", 0.0)
        )

        return outcome

    except Exception as error:
        outcome["status"] = "failed"
        outcome["error"] = str(error)[:2_000]

        return outcome

    finally:
        outcome["total_execution_ms"] = round(
            (perf_counter() - started_at) * 1_000,
            2,
        )