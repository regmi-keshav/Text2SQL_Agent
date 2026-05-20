import argparse
import ast
import json
from pathlib import Path

import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import BASE_DIR, GEMINI_API_KEY, GEMINI_MODEL

try:
    from google import genai
except ImportError as exc:
    raise ImportError(
        "google-genai package is required. Install it with `pip install -r requirements.txt`."
    ) from exc

INPUT_CSV = BASE_DIR / "data" / "sql_questions.csv"
OUTPUT_CSV = BASE_DIR / "data" / "sql_questions_decomposed.csv"

PROMPT_TEMPLATE = """You are an AI assistant that decomposes a natural language question about a SQL database.
Return a strict JSON object with exactly these keys:
- intent
- tables
- columns
- filters
- joins

Use arrays for tables, columns, and joins.
Use a string or array for filters.
Use null when no filters or joins apply.
Do not add explanation, markdown, or extra text.

Question: {question}
"""


def build_prompt(question: str) -> str:
    return PROMPT_TEMPLATE.format(question=question.strip())


def extract_json(text: str) -> dict:
    if isinstance(text, dict):
        return text
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(text)
        except Exception:
            cleaned = text.replace("'", '"')
            return json.loads(cleaned)


def get_response_text(response):
    if isinstance(response, str):
        return response
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text
    if hasattr(response, "text") and response.text:
        return response.text
    if hasattr(response, "output") and response.output:
        output = response.output
        if isinstance(output, (list, tuple)) and output:
            first = output[0]
            if isinstance(first, dict) and "content" in first:
                return "".join(
                    item.get("text", "")
                    for item in first.get("content", [])
                    if isinstance(item, dict)
                )
            return str(first)
        return str(output)
    if hasattr(response, "response") and response.response:
        return get_response_text(response.response)
    return str(response)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def call_gemini(prompt: str) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        chat = client.chats.create(model=GEMINI_MODEL)
        response = chat.send_message(prompt)
    except AttributeError as exc:
        raise RuntimeError(
            "Google Gemini client does not support the expected chat API. "
            "Install a compatible google-genai version."
        ) from exc
    text = get_response_text(response)
    return extract_json(text)


def normalize_field(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value]
    return value


def decompose_questions(input_csv: Path, output_csv: Path):
    df = pd.read_csv(input_csv)
    results = []
    questions = df["question"].astype(str).fillna("").tolist()
    total = len(questions)
    for index, question in enumerate(questions, start=1):
        print(f"Processing question {index}/{total}: {question}")
        prompt = build_prompt(question)
        decomposition = {}
        try:
            decomposition = call_gemini(prompt)
            print(f"  OK")
        except Exception as exc:
            decomposition = {"error": str(exc)}
            print(f"  ERROR: {exc}")
        results.append(
            {
                "question": question,
                "decomposition_json": json.dumps(decomposition, ensure_ascii=False),
                "intent": normalize_field(decomposition.get("intent")),
                "tables": normalize_field(decomposition.get("tables")),
                "columns": normalize_field(decomposition.get("columns")),
                "filters": normalize_field(decomposition.get("filters")),
                "joins": normalize_field(decomposition.get("joins")),
            }
        )
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_csv, index=False)
    print(f"Wrote {len(out_df)} decompositions to {output_csv}")


def main():
    parser = argparse.ArgumentParser(
        description="Decompose SQL questions with Gemini."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_CSV,
        help="CSV file containing the `question` column.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_CSV,
        help="Output CSV file for decomposed JSON results.",
    )
    args = parser.parse_args()
    decompose_questions(args.input, args.output)


if __name__ == "__main__":
    main()
