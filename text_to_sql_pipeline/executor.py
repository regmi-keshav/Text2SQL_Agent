import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .database import execute_sql
from .sql_generator import simple_fix_sql
from .validator import validate_select_query

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
EXECUTION_LOG = LOGS_DIR / "query_execution_log.csv"


@dataclass
class ExecutionResult:
    question: str
    sql: str
    executed_sql: str
    status: str
    error: Optional[str]
    retry_needed: bool
    retry_status: Optional[str]
    retry_error: Optional[str]
    row_count: Optional[int]
    duration_seconds: float
    raw_result: Optional[Any]


def _write_log_row(record: ExecutionResult) -> None:
    fieldnames = [
        "question",
        "sql",
        "executed_sql",
        "status",
        "error",
        "retry_needed",
        "retry_status",
        "retry_error",
        "row_count",
        "duration_seconds",
        "result_preview",
    ]
    write_header = not EXECUTION_LOG.exists()
    with open(EXECUTION_LOG, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "question": record.question,
            "sql": record.sql,
            "executed_sql": record.executed_sql,
            "status": record.status,
            "error": record.error,
            "retry_needed": record.retry_needed,
            "retry_status": record.retry_status,
            "retry_error": record.retry_error,
            "row_count": record.row_count,
            "duration_seconds": f"{record.duration_seconds:.4f}",
            "result_preview": json.dumps((record.raw_result or [])[:3], default=str),
        })


def execute_with_retry(question: str, sql_text: str) -> ExecutionResult:
    retry_needed = False
    first_error = None
    duration_seconds = 0.0
    rows = None
    status = "failed"

    try:
        validate_select_query(sql_text)
        start = time.perf_counter()
        rows = execute_sql(sql_text)
        duration_seconds = time.perf_counter() - start
        status = "success"
        record = ExecutionResult(
            question=question,
            sql=sql_text,
            executed_sql=sql_text,
            status=status,
            error=None,
            retry_needed=False,
            retry_status=None,
            retry_error=None,
            row_count=len(rows) if rows is not None else 0,
            duration_seconds=duration_seconds,
            raw_result=rows,
        )
        _write_log_row(record)
        return record
    except Exception as exc:
        first_error = str(exc)
        retry_needed = True

    fixed_sql = simple_fix_sql(sql_text, first_error)
    retry_status = "failed"
    retry_error = None
    if fixed_sql and fixed_sql != sql_text:
        try:
            validate_select_query(fixed_sql)
            start = time.perf_counter()
            rows = execute_sql(fixed_sql)
            duration_seconds = time.perf_counter() - start
            retry_status = "success"
            status = "success"
            record = ExecutionResult(
                question=question,
                sql=sql_text,
                executed_sql=fixed_sql,
                status=status,
                error=first_error,
                retry_needed=True,
                retry_status=retry_status,
                retry_error=None,
                row_count=len(rows) if rows is not None else 0,
                duration_seconds=duration_seconds,
                raw_result=rows,
            )
            _write_log_row(record)
            return record
        except Exception as retry_exc:
            retry_error = str(retry_exc)
            first_error = first_error or retry_error
    else:
        retry_needed = False

    record = ExecutionResult(
        question=question,
        sql=sql_text,
        executed_sql=fixed_sql if fixed_sql and fixed_sql != sql_text else sql_text,
        status=status,
        error=first_error,
        retry_needed=retry_needed,
        retry_status=retry_status if retry_needed else None,
        retry_error=retry_error,
        row_count=None,
        duration_seconds=duration_seconds,
        raw_result=None,
    )
    _write_log_row(record)
    return record
