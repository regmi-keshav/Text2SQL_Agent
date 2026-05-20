# Text2SQLAgent

## Project Overview

This repository is an early-stage Text-to-SQL project focused on dataset preparation and query decomposition for a SQL benchmark task.

The current implementation is centered around:
- a benchmark question dataset (`data/sql_questions.csv`)
- a Google Gemini-based question decomposition pipeline (`query_decomposition/query_decomposition.py`)
- a record of decomposed structured outputs (`data/sql_questions_decomposed.csv`)

## Requirements Covered

### req1: SQL Benchmark Dataset Preparation and Evaluation Design

Current progress:
- Prepared a benchmark dataset of natural language SQL questions in `data/sql_questions.csv`.
- Included the original benchmark question set PDF in `SQL Benchmark dataset/SQL Benchmark dataset.pdf`.
- Implemented a decomposition pipeline to help parse questions into structured SQL planning components.

Not yet completed in this repository:
- Manual creation of final ground truth SQL queries for each benchmark question.
- Execution output screenshots or exported result verification.
- A full evaluation module for actual Text-to-SQL agent outputs.

Suggested evaluation strategy for the Text-to-SQL agent:
- SQL correctness against ground truth queries
- Execution success / runtime failure detection
- Accuracy of returned result rows
- Correct table/column selection
- Join correctness and filter application
- Error handling and retry/self-correction behavior
- Natural language answer quality if results are converted to text
- Query execution performance
- Robustness to ambiguous or incomplete questions

### req2: Query Understanding (Decomposition Task)

Current progress:
- Built a pipeline to decompose benchmark questions into structured components.
- The decomposition output includes:
  - `intent`
  - `tables`
  - `columns`
  - `filters`
  - `joins`
- Example output is recorded in `data/sql_questions_decomposed.csv`.

This matches the decomposition task by identifying the necessary SQL building blocks before writing a query.

## Project Structure

- `data/sql_questions.csv` — benchmark natural language questions.
- `data/sql_questions_decomposed.csv` — decomposed results produced by the current pipeline.
- `query_decomposition/config.py` — environment configuration for Google Gemini.
- `query_decomposition/query_decomposition.py` — script to decompose questions into JSON components.
- `SQL Benchmark dataset/SQL Benchmark dataset.pdf` — benchmark question dataset reference.
- `sql/seed.sql` — placeholder schema file for future SQL and database setup.
- `requirements.txt` — Python dependencies.

## Setup

1. Create or activate a Python virtual environment.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Create a `.env` file in the repository root with:

```text
GEMINI_API_KEY=<your_api_key>
GEMINI_MODEL=gemini-1.0-mini
```

4. Ensure the `.env` file is present and valid before running the decomposition script.

## Usage

Run the decomposition pipeline with:

```bash
python query_decomposition/query_decomposition.py
```

Optional arguments:

- `--input` — input CSV file path (default: `data/sql_questions.csv`)
- `--output` — output CSV file path (default: `data/sql_questions_decomposed.csv`)

Example:

```bash
python query_decomposition/query_decomposition.py --input data/sql_questions.csv --output data/sql_questions_decomposed.csv
```

## What Has Been Done So Far

- Collected benchmark questions into `data/sql_questions.csv`.
- Built a Gemini-based question decomposition pipeline.
- Generated structured decomposition output for each question.
- Captured the main decomposition fields needed to support SQL planning.

## Next Steps

To fully satisfy `req1` and `req2`, the next work items are:

1. Create and store ground truth SQL queries for all benchmark questions.
2. Execute queries against a real PostgreSQL schema and verify results.
3. Add a formal evaluation strategy implementation for Text-to-SQL outputs.
4. Expand the project into actual SQL generation and answer retrieval.

## Notes

- The project currently focuses on question understanding and structure rather than SQL generation.
- This README is aligned with the current repository state and the target benchmark tasks.
