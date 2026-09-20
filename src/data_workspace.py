from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def clean_table_name(name: str) -> str:
    """Convert a filename or sheet name into a safe SQL table name."""

    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", name)
    cleaned = cleaned.strip("_").lower()

    if not cleaned:
        cleaned = "table"

    if cleaned[0].isdigit():
        cleaned = f"table_{cleaned}"

    return cleaned