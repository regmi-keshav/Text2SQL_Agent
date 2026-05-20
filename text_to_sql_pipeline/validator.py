import re

FORBIDDEN_STATEMENTS = re.compile(
    r"\b(delete|update|insert|drop|alter|create|truncate|replace|grant|revoke)\b",
    re.IGNORECASE,
)


def validate_select_query(sql_text: str) -> None:
    if not sql_text or not isinstance(sql_text, str):
        raise ValueError("SQL query must be a non-empty string.")
    cleaned = sql_text.strip()
    if cleaned.endswith(";"):
        raise ValueError("SQL query must not include a trailing semicolon.")
    if not cleaned.lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN_STATEMENTS.search(cleaned):
        raise ValueError("Query contains forbidden SQL operations.")
    if "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise ValueError("SQL comments are not permitted in generated queries.")
