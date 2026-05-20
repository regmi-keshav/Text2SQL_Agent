import ast
import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from .executor import execute_with_retry
from .sql_generator import generate_sql

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = BASE_DIR / "data" / "sql_questions_decomposed.csv"
REPORT_CSV = BASE_DIR / "logs" / "query_execution_report.csv"
RESULTS_JSON = BASE_DIR / "logs" / "query_execution_results.json"


def parse_decomposition(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    text = str(value).strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(text)
        except Exception:
            return {}


def build_row_decomposition(row: pd.Series) -> Dict[str, Any]:
    decomposition = parse_decomposition(row.get("decomposition_json"))
    if decomposition:
        return decomposition
    return {
        "intent": row.get("intent"),
        "tables": row.get("tables"),
        "columns": row.get("columns"),
        "filters": row.get("filters"),
        "joins": row.get("joins"),
    }


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    report_rows = []
    result_rows = []

    for index, row in df.iterrows():
        question = str(row.get("question", "")).strip()
        decomposition = build_row_decomposition(row)
        try:
            sql_text = generate_sql(decomposition)
        except Exception as exc:
            report_rows.append(
                {
                    "question": question,
                    "sql": None,
                    "executed_sql": None,
                    "status": "failed",
                    "executed_successfully": False,
                    "retry_needed": False,
                    "retry_status": None,
                    "row_count": None,
                    "duration_seconds": None,
                    "correct_result": None,
                    "final_status": "failed",
                    "error": f"SQL generation failed: {exc}",
                }
            )
            result_rows.append(
                {
                    "question": question,
                    "sql": None,
                    "executed_sql": None,
                    "result": None,
                    "status": "failed",
                    "error": f"SQL generation failed: {exc}",
                }
            )
            continue

        result = execute_with_retry(question, sql_text)
        report_rows.append(
            {
                "question": question,
                "sql": sql_text,
                "executed_sql": result.executed_sql,
                "status": result.status,
                "executed_successfully": result.status == "success",
                "retry_needed": result.retry_needed,
                "retry_status": result.retry_status,
                "row_count": result.row_count,
                "duration_seconds": result.duration_seconds,
                "correct_result": None,
                "final_status": result.status,
                "error": result.error or result.retry_error,
            }
        )
        result_rows.append(
            {
                "question": question,
                "sql": sql_text,
                "executed_sql": result.executed_sql,
                "result": result.raw_result,
                "status": result.status,
                "error": result.error or result.retry_error,
            }
        )

    report_dir = REPORT_CSV.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(report_rows).to_csv(REPORT_CSV, index=False)
    RESULTS_JSON.write_text(json.dumps(result_rows, indent=2, default=str), encoding="utf-8")
    summary = {
        "total_questions": len(report_rows),
        "success_count": sum(1 for item in report_rows if item["status"] == "success"),
        "failed_count": sum(1 for item in report_rows if item["status"] != "success"),
        "retry_count": sum(1 for item in report_rows if item["retry_needed"]),
    }
    print("Text-to-SQL pipeline finished.")
    print(f"Report saved to: {REPORT_CSV}")
    print(f"Detailed results saved to: {RESULTS_JSON}")
    print(f"Total questions: {summary['total_questions']}")
    print(f"Successful queries: {summary['success_count']}")
    print(f"Failed queries: {summary['failed_count']}")
    print(f"Queries needing retry: {summary['retry_count']}")


if __name__ == "__main__":
    main()
