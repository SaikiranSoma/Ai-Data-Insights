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

def unique_table_name(base_name: str, existing_names: set[str]) -> str:
    """Prevent tables from overwriting each other."""

    name = base_name
    counter = 2

    while name in existing_names:
        name = f"{base_name}_{counter}"
        counter += 1

    return name