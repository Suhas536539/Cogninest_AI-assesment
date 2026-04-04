# Clinic NL2SQL Assignment

This project implements a clinic analytics Natural Language to SQL backend using FastAPI, SQLite, Plotly, and Vanna 2.0-style agent setup. It includes:

- `setup_database.py` to create and populate `clinic.db`
- `seed_memory.py` to generate 15 benchmark Q&A pairs for memory seeding
- `vanna_setup.py` to initialize a Vanna 2.0 agent with Gemini, SQLite, DemoAgentMemory, and a strict read-only SQL runner
- `main.py` to serve the REST API and optional mounted Vanna UI routes
- `RESULTS.md` with the 20 required benchmark questions and outcomes

## Chosen LLM Provider

- Provider: Google Gemini
- Model: `gemini-2.5-flash`
- Environment variable: `GOOGLE_API_KEY`

## Project Structure

```text
project/
  clinic.db
  clinic_nl2sql.py
  main.py
  memory_seed.json
  README.md
  requirements.txt
  RESULTS.md
  seed_memory.py
  setup_database.py
  sql_validation.py
  vanna_setup.py
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Add your Gemini key to a `.env` file.
4. Build the database.
5. Seed the benchmark memory file.
6. Start the API server.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```env
GOOGLE_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.5-flash
```

Build and run:

```bash
python setup_database.py
python seed_memory.py
uvicorn main:app --port 8000
```

The assignment command also works:

```bash
pip install -r requirements.txt && python setup_database.py && python seed_memory.py && uvicorn main:app --port 8000
```

## How Memory Seeding Works

`DemoAgentMemory` is in-memory only, so `seed_memory.py` writes the 15 benchmark examples into `memory_seed.json`. On application startup, `vanna_setup.py` loads that file and inserts the examples into `DemoAgentMemory`, along with one schema note.

## API

### `POST /chat`

Request:

```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

Response shape:

```json
{
  "message": "Found 5 row(s) for 'Show me the top 5 patients by total spending'.",
  "sql_query": "SELECT ...",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [["Myra", "Gupta", 29364.55]],
  "row_count": 5,
  "chart": { "data": [], "layout": {} },
  "chart_type": "bar",
  "cached": false
}
```

### `GET /health`

Example response:

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 16,
  "vanna_agent_configured": true,
  "llm_provider": "Gemini"
}
```

## Optional Vanna UI

If `GOOGLE_API_KEY` is configured, the app mounts a Vanna FastAPI app at `/vanna`. That gives you Vanna’s built-in UI and streaming endpoints in addition to the assignment-friendly `/chat` endpoint.

## Architecture Overview

```text
Question
  -> FastAPI /chat
  -> question normalization and benchmark routing
  -> SQL validation (SELECT-only, no dangerous keywords/system tables)
  -> SQLite execution
  -> Plotly chart generation when appropriate
  -> JSON response
```

When Gemini is configured:

```text
Question
  -> Vanna Agent
  -> ToolRegistry
  -> RunSqlTool with SafeSqliteRunner
  -> DemoAgentMemory seeded from memory_seed.json
  -> optional Vanna UI at /vanna
```

## SQL Safety and Error Handling

- Only `SELECT` and safe `WITH ... SELECT` queries are allowed.
- Dangerous operations such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `EXEC`, `PRAGMA`, and system table access are rejected.
- Empty questions and overly long questions are blocked by request validation.
- Database execution errors are caught and returned as API errors.
- Empty results return a friendly `No data found` message.

## Bonus Features Included

- Plotly chart generation for trend/comparison questions
- Request validation
- In-memory query caching
- Simple in-memory rate limiting
- Structured logging

## Notes

- The published benchmark question "Average appointment duration by doctor" is answered using `treatments.duration_minutes` because the provided schema does not include an appointment-duration column.
- Doctor/department revenue is computed from treatment costs because `invoices` are linked only to patients, not to appointments or doctors.
