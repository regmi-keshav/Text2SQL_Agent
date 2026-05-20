# Text2SQLAgent

## Overview

This repository implements a simple Text-to-SQL pipeline for the benchmark question set in `data/sql_questions.csv`.

The pipeline follows this flow:

Natural language question  
-> structured decomposition  
-> SQL generation  
-> PostgreSQL execution  
-> validation and one retry  
-> logged results and benchmark report

## Task 3 Coverage

The current pipeline includes:

- structured decomposition input from `data/sql_questions_decomposed.csv`
- automatic SQL generation for `SELECT` queries
- aggregate query support for `COUNT`, `SUM`, `AVG`, `MIN`, and `MAX`
- schema-aware identifier normalization using `sql/seed.sql`
- PostgreSQL query execution
- query safety validation that blocks non-`SELECT` statements
- one retry attempt for recoverable SQL issues
- CSV execution logging
- benchmark report generation
- JSON export of executed results

## Project Structure

- `data/sql_questions.csv` - benchmark questions
- `data/sql_questions_decomposed.csv` - decomposed benchmark questions
- `query_decomposition/query_decomposition.py` - Gemini-based decomposition script
- `sql/seed.sql` - PostgreSQL schema and seed data
- `text_to_sql_pipeline/database.py` - database connection and execution helpers
- `text_to_sql_pipeline/schema.py` - local schema metadata loader from `sql/seed.sql`
- `text_to_sql_pipeline/sql_generator.py` - decomposition-to-SQL conversion
- `text_to_sql_pipeline/validator.py` - SQL safety validation
- `text_to_sql_pipeline/executor.py` - execution, retry handling, and logging
- `text_to_sql_pipeline/main.py` - benchmark runner
- `run_pipeline.py` - top-level entrypoint
- `logs/` - generated execution logs, reports, and result exports

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Create a `.env` file in the repository root:

```text
GEMINI_API_KEY=<your_api_key>
GEMINI_MODEL=gemini-1.0-mini
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=<your_database>
POSTGRES_USER=<your_user>
POSTGRES_PASSWORD=<your_password>
POSTGRES_SSLMODE=prefer
```

4. Load the schema and sample data into PostgreSQL using `sql/seed.sql`.

## Usage

Generate decompositions:

```bash
python query_decomposition/query_decomposition.py
```

Run the benchmark pipeline:

```bash
python run_pipeline.py
```

## Outputs

After a successful run, the pipeline writes:

- `logs/query_execution_log.csv` - per-query execution log
- `logs/query_execution_report.csv` - benchmark report table
- `logs/query_execution_results.json` - structured results with returned rows

## Evaluation Notes

The benchmark report includes the main execution fields needed for Task 3:

- question
- generated SQL
- executed SQL
- execution status
- whether retry was needed
- retry status
- row count
- latency
- final status
- error details

To complete correctness benchmarking, compare pipeline outputs against manually verified SQL or expected result sets for the benchmark questions.
