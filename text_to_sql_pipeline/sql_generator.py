import ast
import json
import re
from typing import Any, Dict, List, Optional, Sequence, Union

from .schema import normalize_table_name, quote_identifier, resolve_column_name

AGGREGATE_PATTERN = re.compile(
    r"^(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*|\*)\s*\)$",
    re.IGNORECASE,
)


def as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if item is not None]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                decoded = json.loads(text)
                return [str(item).strip() for item in decoded if item is not None]
            except json.JSONDecodeError:
                try:
                    decoded = ast.literal_eval(text)
                    return [str(item).strip() for item in decoded if item is not None]
                except Exception:
                    pass
        return [text]
    return [str(value).strip()]


def build_select_clause(columns: Sequence[str]) -> str:
    normalized = [normalize_expression(col.strip()) for col in columns if col and col.strip()]
    if not normalized:
        return "SELECT *"
    if len(normalized) == 1 and normalized[0] == "*":
        return "SELECT *"
    return "SELECT " + ", ".join(normalized)


def build_from_clause(tables: Sequence[str], joins: Sequence[str]) -> str:
    normalized_tables = [normalize_table_name(table.strip()) for table in tables if table and table.strip()]
    if not normalized_tables:
        raise ValueError("No tables found in decomposition.")
    if len(normalized_tables) == 1:
        return f"FROM {normalized_tables[0]}"
    if joins:
        base_table = normalized_tables[0]
        join_clauses = []
        for index, next_table in enumerate(normalized_tables[1:], start=0):
            condition = normalize_condition(joins[index]) if index < len(joins) else ""
            if condition:
                join_clauses.append(f"JOIN {next_table} ON {condition}")
            else:
                join_clauses.append(f"JOIN {next_table}")
        return f"FROM {base_table} " + " ".join(join_clauses)
    return "FROM " + ", ".join(normalized_tables)


def build_where_clause(filters: Union[str, Sequence[str], None]) -> str:
    if not filters:
        return ""
    conditions: List[str] = []
    if isinstance(filters, str):
        if filters.strip():
            conditions = [normalize_condition(filters.strip())]
    elif isinstance(filters, (list, tuple)):
        conditions = [
            normalize_condition(str(item).strip())
            for item in filters
            if item and str(item).strip()
        ]
    else:
        conditions = [normalize_condition(str(filters).strip())]
    if not conditions:
        return ""
    return "WHERE " + " AND ".join(conditions)


def build_group_by_clause(columns: Sequence[str]) -> str:
    groupable_columns = []
    for column in columns:
        cleaned = column.strip()
        if not cleaned or AGGREGATE_PATTERN.match(cleaned):
            continue
        normalized = normalize_expression(cleaned)
        if normalized != "*":
            groupable_columns.append(normalized)
    if not groupable_columns:
        return ""
    return "GROUP BY " + ", ".join(groupable_columns)


def normalize_expression(expression: str) -> str:
    cleaned = (expression or "").strip()
    if not cleaned:
        return cleaned
    if cleaned == "*":
        return "*"
    aggregate_match = AGGREGATE_PATTERN.match(cleaned)
    if aggregate_match:
        function_name, argument = aggregate_match.groups()
        if argument == "*":
            return f"{function_name.upper()}(*)"
        return f"{function_name.upper()}({quote_column_reference(argument)})"
    return quote_column_reference(cleaned)


def normalize_condition(condition: str) -> str:
    text = (condition or "").strip()
    if not text:
        return ""

    parts = re.split(r"(\s+)", text)
    normalized_parts: List[str] = []
    for part in parts:
        stripped = part.strip()
        if not stripped:
            normalized_parts.append(part)
            continue
        if stripped.upper() in {"AND", "OR", "IN", "LIKE", "IS", "NOT", "NULL", "BETWEEN"}:
            normalized_parts.append(stripped.upper())
            continue
        if stripped in {"=", "!=", "<>", ">", "<", ">=", "<=", "(", ")", ","}:
            normalized_parts.append(stripped)
            continue
        if stripped.startswith("'") and stripped.endswith("'"):
            normalized_parts.append(stripped)
            continue
        if re.fullmatch(r"-?\d+(\.\d+)?", stripped):
            normalized_parts.append(stripped)
            continue
        if "." in stripped and not stripped.endswith("."):
            normalized_parts.append(quote_column_reference(stripped))
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stripped):
            normalized_parts.append(quote_column_reference(stripped))
            continue
        normalized_parts.append(stripped)

    return "".join(normalized_parts)


def quote_column_reference(reference: str) -> str:
    cleaned = (reference or "").strip()
    if not cleaned:
        return cleaned
    if "." not in cleaned:
        resolved = resolve_column_name(cleaned)
        return quote_identifier(resolved)

    table_name, column_name = cleaned.split(".", 1)
    normalized_table = normalize_table_name(table_name)
    resolved_column = resolve_column_name(column_name, table_name=normalized_table)
    return f"{normalized_table}.{quote_identifier(resolved_column)}"


def generate_sql(decomposition: Dict[str, Any]) -> str:
    intent = decomposition.get("intent")
    tables = as_list(decomposition.get("tables"))
    columns = as_list(decomposition.get("columns"))
    filters = decomposition.get("filters")
    joins = as_list(decomposition.get("joins"))

    select_clause = build_select_clause(columns)
    from_clause = build_from_clause(tables, joins)
    where_clause = build_where_clause(filters)
    group_by_clause = build_group_by_clause(columns) if "AGGREGATE" in str(intent).upper() else ""

    sql_parts = [select_clause, from_clause]
    if where_clause:
        sql_parts.append(where_clause)
    if group_by_clause:
        sql_parts.append(group_by_clause)
    sql_text = " ".join(sql_parts).strip()
    return sql_text


def simple_fix_sql(sql_text: str, error_message: str) -> Optional[str]:
    lowered = error_message.lower()
    cleaned = sql_text.strip()
    if cleaned.endswith(";"):
        return cleaned.rstrip(";")
    if "must appear in the group by clause" in lowered and "group by" not in cleaned.lower():
        select_text = cleaned[6:].strip()
        from_index = select_text.lower().find(" from ")
        if from_index != -1:
            select_columns = []
            for item in select_text[:from_index].split(","):
                candidate = item.strip()
                if "(" not in candidate:
                    select_columns.append(candidate)
            group_by_clause = "GROUP BY " + ", ".join(select_columns) if select_columns else ""
            if group_by_clause:
                return f"{cleaned} {group_by_clause}"
    if "syntax error at or near" in lowered:
        return cleaned
    return None
