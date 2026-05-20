import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_SQL = BASE_DIR / "sql" / "seed.sql"

CREATE_TABLE_PATTERN = re.compile(
    r"CREATE TABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\);",
    re.IGNORECASE | re.DOTALL,
)
COLUMN_PATTERN = re.compile(r'^\s*"([^"]+)"\s+', re.MULTILINE)


@lru_cache(maxsize=1)
def load_schema() -> Dict[str, Dict[str, str]]:
    if not SEED_SQL.exists():
        return {}

    sql_text = SEED_SQL.read_text(encoding="utf-8")
    schema: Dict[str, Dict[str, str]] = {}

    for table_name, body in CREATE_TABLE_PATTERN.findall(sql_text):
        column_map = {column.lower(): column for column in COLUMN_PATTERN.findall(body)}
        schema[table_name.lower()] = {
            "table_name": table_name,
            "columns": column_map,
        }

    return schema


def normalize_table_name(table_name: str) -> str:
    text = (table_name or "").strip()
    if not text:
        raise ValueError("Table name cannot be empty.")

    schema = load_schema()
    table_info = schema.get(text.lower())
    return table_info["table_name"] if table_info else text


def quote_identifier(identifier: str) -> str:
    if not identifier:
        raise ValueError("Identifier cannot be empty.")
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def resolve_column_name(column_name: str, table_name: Optional[str] = None) -> str:
    cleaned = (column_name or "").strip()
    if not cleaned:
        raise ValueError("Column name cannot be empty.")

    schema = load_schema()
    if table_name:
        table_info = schema.get(table_name.lower())
        if table_info:
            return table_info["columns"].get(cleaned.lower(), cleaned)

    matches: List[str] = []
    for table_info in schema.values():
        actual_name = table_info["columns"].get(cleaned.lower())
        if actual_name and actual_name not in matches:
            matches.append(actual_name)

    if len(matches) == 1:
        return matches[0]
    return cleaned
