from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections import deque
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from clinic_nl2sql import normalize_question, translate_question
from sql_validation import validate_select_sql
from vanna_setup import build_agent, create_tool_context


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("clinic-nl2sql")
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "clinic.db"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    message: str
    sql_query: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    chart: dict[str, Any] | None = None
    chart_type: str | None = None
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    database: str
    agent_memory_items: int
    vanna_agent_configured: bool
    llm_provider: str


class SimpleRateLimiter:
    def __init__(self, limit: int = 20, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}

    def check(self, key: str) -> None:
        now = time.time()
        bucket = self._events.setdefault(key, deque())
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry shortly.")
        bucket.append(now)


def execute_sql(sql: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(sql, connection)


def rows_from_frame(frame: pd.DataFrame) -> list[list[Any]]:
    values = frame.where(pd.notnull(frame), None)
    return values.values.tolist()


def summarize_results(question: str, frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No data found for that question."
    if len(frame) == 1 and len(frame.columns) == 1:
        return f"The answer to '{question}' is {frame.iloc[0, 0]}."
    return f"Found {len(frame)} row(s) for '{question}'."


def build_chart(question: str, frame: pd.DataFrame) -> tuple[dict[str, Any] | None, str | None]:
    if frame.empty or len(frame.columns) < 2:
        return None, None

    normalized = normalize_question(question)
    x = frame.columns[0]
    y = frame.columns[1]

    if any(keyword in normalized for keyword in ["trend", "monthly", "past 6 months", "registration"]):
        figure = px.line(frame, x=x, y=y, markers=True, title=question)
        return json.loads(json.dumps(figure.to_plotly_json(), cls=PlotlyJSONEncoder)), "line"

    if any(keyword in normalized for keyword in ["top 5", "revenue by", "compare revenue", "city", "busiest"]):
        figure = px.bar(frame, x=x, y=y, title=question)
        return json.loads(json.dumps(figure.to_plotly_json(), cls=PlotlyJSONEncoder)), "bar"

    return None, None


async def count_memory_items(agent_memory: Any) -> int:
    context = create_tool_context(agent_memory)
    memories = await agent_memory.get_recent_memories(context, limit=5000)
    text_memories = await agent_memory.get_recent_text_memories(context, limit=5000)
    return len(memories) + len(text_memories)


agent, agent_memory, agent_metadata = build_agent()
rate_limiter = SimpleRateLimiter()
response_cache: dict[str, ChatResponse] = {}

app = FastAPI(title="Clinic NL2SQL API", version="1.0.0")

if agent is not None:
    from vanna.servers.fastapi import VannaFastAPIServer

    app.mount("/vanna", VannaFastAPIServer(agent).create_app())


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    vanna_status = "Available" if agent is not None else "Unavailable until GOOGLE_API_KEY is configured"
    return f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Clinic NL2SQL API</title>
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f6f8fb;
            color: #1f2937;
            margin: 0;
            padding: 40px 20px;
          }}
          .card {{
            max-width: 860px;
            margin: 0 auto;
            background: white;
            border-radius: 18px;
            padding: 32px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
          }}
          h1 {{ margin-top: 0; }}
          .links a {{
            display: inline-block;
            margin: 8px 12px 8px 0;
            padding: 12px 16px;
            border-radius: 10px;
            text-decoration: none;
            background: #0f172a;
            color: white;
          }}
          code {{
            background: #eef2ff;
            padding: 2px 6px;
            border-radius: 6px;
          }}
          ul {{
            line-height: 1.7;
          }}
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Clinic NL2SQL Assignment</h1>
          <p>This service converts natural-language clinic analytics questions into safe SQL results over a SQLite database.</p>
          <div class="links">
            <a href="/docs">Open API Docs</a>
            <a href="/health">Health Check</a>
            <a href="/vanna/">Open Vanna UI</a>
          </div>
          <ul>
            <li><strong>REST endpoint:</strong> <code>POST /chat</code></li>
            <li><strong>Health endpoint:</strong> <code>GET /health</code></li>
            <li><strong>Vanna UI:</strong> <code>/vanna/</code></li>
            <li><strong>LLM provider:</strong> {agent_metadata["provider"]} ({agent_metadata["model"]})</li>
            <li><strong>Vanna status:</strong> {vanna_status}</li>
          </ul>
          <p>Example question: <code>Show revenue by doctor</code></p>
        </div>
      </body>
    </html>
    """


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    database = "connected" if DB_PATH.exists() else "missing"
    return HealthResponse(
        status="ok",
        database=database,
        agent_memory_items=await count_memory_items(agent_memory),
        vanna_agent_configured=bool(agent),
        llm_provider=agent_metadata["provider"],
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="clinic.db was not found. Run setup_database.py first.")

    rate_limiter.check(request.client.host if request.client else "local")

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    cache_key = normalize_question(question)
    cached = response_cache.get(cache_key)
    if cached is not None:
        return cached.model_copy(update={"cached": True})

    sql = translate_question(question)
    if not sql:
        raise HTTPException(
            status_code=400,
            detail=(
                "This assignment endpoint currently supports the provided benchmark questions and close variations. "
                "For free-form experimentation, configure GOOGLE_API_KEY and use the mounted Vanna UI at /vanna."
            ),
        )

    try:
        sql = validate_select_sql(sql)
        frame = execute_sql(sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid SQL generated: {exc}") from exc
    except Exception as exc:
        LOGGER.exception("Database execution failed")
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    chart, chart_type = build_chart(question, frame)
    response = ChatResponse(
        message=summarize_results(question, frame),
        sql_query=sql,
        columns=list(frame.columns),
        rows=rows_from_frame(frame),
        row_count=len(frame),
        chart=chart,
        chart_type=chart_type,
    )
    response_cache[cache_key] = response
    return response
