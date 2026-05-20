import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.decomposer import decompose_question
from api.models import AgentAttemptLog, AgentRunLog, SQLAgentResponse
from text_to_sql_pipeline.database import execute_sql
from text_to_sql_pipeline.sql_generator import generate_sql, simple_fix_sql
from text_to_sql_pipeline.validator import validate_select_query

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
AGENT_LOG = LOGS_DIR / "agent_sql_log.jsonl"
MAX_AGENT_RETRIES = 3


def run_sql_agent(question: str) -> SQLAgentResponse:
    decomposition = decompose_question(question)
    current_sql = generate_sql(decomposition)
    attempts: List[AgentAttemptLog] = []
    final_result: Optional[Any] = None
    last_error: Optional[str] = None

    for attempt_number in range(1, MAX_AGENT_RETRIES + 1):
        started_at = time.perf_counter()
        try:
            validate_select_query(current_sql)
            rows = execute_sql(current_sql)
            duration_seconds = time.perf_counter() - started_at
            attempts.append(
                AgentAttemptLog(
                    attempt=attempt_number,
                    sql=current_sql,
                    status="success",
                    duration_seconds=duration_seconds,
                )
            )
            final_result = shape_result(rows)
            response = SQLAgentResponse(
                sql=current_sql,
                result=final_result,
                summary=build_summary(question, final_result),
                status="success",
                attempts=attempt_number,
                error=None,
            )
            write_agent_log(
                question=question,
                decomposition=decomposition,
                attempts=attempts,
                final_status="success",
                summary=response.summary,
            )
            return response
        except Exception as exc:
            duration_seconds = time.perf_counter() - started_at
            last_error = str(exc)
            attempts.append(
                AgentAttemptLog(
                    attempt=attempt_number,
                    sql=current_sql,
                    status="failed",
                    error=last_error,
                    duration_seconds=duration_seconds,
                )
            )
            if attempt_number == MAX_AGENT_RETRIES:
                break
            fixed_sql = simple_fix_sql(current_sql, last_error)
            if fixed_sql and fixed_sql != current_sql:
                current_sql = fixed_sql
                continue
            current_sql = regenerate_sql_from_error(decomposition, current_sql, last_error)

    fallback_summary = "I could not complete the SQL request after 3 attempts."
    write_agent_log(
        question=question,
        decomposition=decomposition,
        attempts=attempts,
        final_status="failed",
        summary=fallback_summary,
    )
    return SQLAgentResponse(
        sql=current_sql,
        result=None,
        summary=fallback_summary,
        status="failed",
        attempts=MAX_AGENT_RETRIES,
        error=last_error,
    )


def regenerate_sql_from_error(decomposition: Dict[str, Any], current_sql: str, error_message: str) -> str:
    lowered = error_message.lower()

    if "must appear in the group by clause" in lowered and "AGGREGATE" not in str(decomposition.get("intent", "")).upper():
        decomposition = {**decomposition, "intent": "AGGREGATE_COUNT"}
        if not decomposition.get("columns"):
            decomposition["columns"] = ["COUNT(*)"]
        return generate_sql(decomposition)

    if "column" in lowered and "does not exist" in lowered and decomposition.get("columns") == ["*"]:
        return current_sql

    if "join" not in current_sql.lower() and len(decomposition.get("tables") or []) > 1:
        return generate_sql(decomposition)

    return current_sql


def shape_result(rows: List[Dict[str, Any]]) -> Any:
    if not rows:
        return []
    if len(rows) == 1 and len(rows[0]) == 1:
        return next(iter(rows[0].values()))
    return rows


def build_summary(question: str, result: Any) -> str:
    normalized_question = (question or "").strip().rstrip("?")
    lowered = normalized_question.lower()
    if isinstance(result, (int, float)):
        if lowered.startswith("how many"):
            subject = normalized_question[8:].strip()
            return f"There are {result} {subject}."
        if lowered.startswith("count"):
            return f"The count is {result}."
        return f"The result is {result}."
    if isinstance(result, list):
        if not result:
            return f"No results were found for '{normalized_question}'."
        return f"The query returned {len(result)} rows for '{normalized_question}'."
    return f"The query result for '{normalized_question}' is {result}."


def write_agent_log(
    question: str,
    decomposition: Dict[str, Any],
    attempts: List[AgentAttemptLog],
    final_status: str,
    summary: str,
) -> None:
    payload = AgentRunLog(
        question=question,
        decomposition=decomposition,
        attempts=attempts,
        final_status=final_status,
        summary=summary,
    )
    with AGENT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(payload.model_dump_json())
        handle.write("\n")
