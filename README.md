# Text2SQLAgent

## Overview

Text2SQLAgent is a lightweight PostgreSQL question-answering system built around a staged Text-to-SQL workflow. It combines benchmark preparation, structured query decomposition, SQL generation, guarded execution, retry-based correction, and an interactive API layer.

The repository serves two complementary purposes:

- offline evaluation and benchmark execution over a stable question set
- interactive natural-language querying through a FastAPI service

At a high level, the system follows this flow:

Natural language question  
-> structured understanding  
-> SQL generation  
-> safety validation  
-> PostgreSQL execution  
-> retry and correction  
-> result formatting and logging

## Project Progression

The repository reflects a staged build-up of the system:

1. A benchmark question set and PostgreSQL schema were prepared to support repeatable evaluation.
2. Questions were decomposed into structured representations containing intent, tables, columns, filters, and joins.
3. A reusable SQL pipeline was implemented to turn decompositions into executable PostgreSQL queries with validation, retry behavior, and logging.
4. An API layer was added to expose the same workflow as an interactive SQL agent.

Key assets involved in this progression include:

- `data/sql_questions.csv`
- `data/sql_questions_decomposed.csv`
- `query_decomposition/`
- `sql/seed.sql`
- `text_to_sql_pipeline/`
- `api/`

## Architecture

The codebase is organized to keep API concerns, SQL engine logic, and evaluation assets separate.

```text
project/
├── api/
│   ├── __init__.py
│   ├── app.py
│   ├── models.py
│   ├── service.py
│   └── decomposer.py
├── text_to_sql_pipeline/
│   ├── __init__.py
│   ├── database.py
│   ├── schema.py
│   ├── sql_generator.py
│   ├── validator.py
│   ├── executor.py
│   └── main.py
├── query_decomposition/
├── data/
├── logs/
├── sql/
├── run_api.py
├── run_pipeline.py
└── README.md
```

### `api/`

The API layer provides interactive access to the SQL agent.

- `app.py` defines the FastAPI application and routes
- `models.py` contains request, response, and log models
- `service.py` orchestrates decomposition, SQL generation, execution, retries, and summaries
- `decomposer.py` performs rule-based question understanding for API requests

### `text_to_sql_pipeline/`

This package contains the reusable SQL execution engine shared by the dataset runner and API.

- `database.py` manages PostgreSQL connections and query execution
- `schema.py` parses schema metadata from `sql/seed.sql`
- `sql_generator.py` converts structured decomposition into executable SQL
- `validator.py` enforces safe, read-only query validation
- `executor.py` handles execution, retry behavior, and logging
- `main.py` runs the dataset-driven pipeline

### Supporting Assets

- `query_decomposition/` generates structured decompositions from benchmark questions using Gemini
- `data/` stores benchmark questions and decomposition outputs
- `sql/` contains the PostgreSQL schema and seed data
- `logs/` stores execution logs, reports, and structured runtime outputs

## Capabilities

The current implementation supports:

- structured SQL generation from decomposed query components
- `SELECT`-only query validation for safe execution
- schema-aware SQL generation for PostgreSQL identifiers
- aggregate query support with `COUNT`, `SUM`, `AVG`, `MIN`, and `MAX`
- `WHERE`, `JOIN`, and `GROUP BY` generation where applicable
- batch execution over benchmark-style inputs
- retry-based correction for failed SQL execution
- natural-language result summaries for API responses
- structured execution logging for both pipeline and API flows

## Batch Pipeline

The batch pipeline runs decomposed benchmark questions against PostgreSQL.

### Responsibilities

- load decomposed benchmark inputs
- generate executable SQL
- validate read-only safety
- execute against PostgreSQL
- retry once on failure when possible
- export logs and execution reports

### Entry Point

- `run_pipeline.py`

### Run

```bash
python run_pipeline.py
```

### Outputs

- `logs/query_execution_log.csv`
- `logs/query_execution_report.csv`
- `logs/query_execution_results.json`

## API Service

The API exposes an interactive SQL agent over HTTP.

### Endpoint

```http
POST /agent/sql
```

### Request

```json
{
  "question": "How many shipped orders are from USA customers?"
}
```

### Behavior

For each request, the service:

1. interprets the question through structured decomposition
2. generates SQL from that structure
3. validates the query as safe and read-only
4. executes it against PostgreSQL
5. retries up to 3 times on failure
6. returns both machine-readable output and a natural-language summary

### Example Response Shape

```json
{
  "sql": "SELECT COUNT(\"orderNumber\") FROM orders JOIN customers ON orders.\"customerNumber\" = customers.\"customerNumber\" WHERE orders.\"status\" = 'Shipped' AND customers.\"country\" = 'USA'",
  "result": 42,
  "summary": "There are 42 shipped orders from customers in USA.",
  "status": "success",
  "attempts": 1,
  "error": null
}
```

### Entry Point

- `run_api.py`

### Run

```bash
python run_api.py
```

Example request:

```bash
curl -X POST http://localhost:8000/agent/sql \
  -H "Content-Type: application/json" \
  -d '{"question":"How many shipped orders are from USA customers?"}'
```

### API Logs

- `logs/agent_sql_log.jsonl`

## Setup

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Configure Environment

Create a `.env` file in the repository root:

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

### Load the Database

Use `sql/seed.sql` to create and seed the PostgreSQL schema used by the project.

## Outputs

The repository produces the following runtime artifacts:

- `logs/query_execution_log.csv` - batch query execution log
- `logs/query_execution_report.csv` - batch benchmark report
- `logs/query_execution_results.json` - batch structured results
- `logs/agent_sql_log.jsonl` - API decomposition, SQL attempts, timings, and outcome

## Evaluation Perspective

The repository is designed to support evaluation of Text-to-SQL behavior from multiple angles, including:

- SQL generation quality
- execution success rate
- result accuracy
- table and column selection quality
- join and filter correctness
- retry and correction behavior
- latency and operational robustness

## Current Limitations

- The API decomposition layer is currently rule-based and intentionally lightweight.
- Query repair logic is still basic and can be improved for more complex failures.
- Fully automated ground-truth benchmarking is not yet implemented in the repository.
- End-to-end execution requires a running PostgreSQL instance and valid local environment configuration.
