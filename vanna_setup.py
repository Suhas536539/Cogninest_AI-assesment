from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.tool import ToolContext
from vanna.core.user import RequestContext, User, UserResolver
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.sqlite import SqliteRunner
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SaveTextMemoryTool,
    SearchSavedCorrectToolUsesTool,
)

from sql_validation import validate_select_sql


LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "clinic.db"
SEED_PATH = BASE_DIR / "memory_seed.json"


class DefaultUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="default-user",
            username="default-user",
            email="default@local",
            group_memberships=["admin", "user"],
        )


class SafeSqliteRunner(SqliteRunner):
    async def run_sql(self, args: Any, context: ToolContext):
        args.sql = validate_select_sql(args.sql)
        return await super().run_sql(args, context)


def create_tool_context(agent_memory: DemoAgentMemory) -> ToolContext:
    return ToolContext(
        user=User(
            id="default-user",
            username="default-user",
            email="default@local",
            group_memberships=["admin", "user"],
        ),
        conversation_id="memory-seed",
        request_id=str(uuid4()),
        agent_memory=agent_memory,
    )


async def seed_agent_memory(agent_memory: DemoAgentMemory) -> int:
    if not SEED_PATH.exists():
        LOGGER.warning("memory_seed.json was not found; agent memory will start empty.")
        return 0

    records = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    context = create_tool_context(agent_memory)
    seeded_count = 0
    for record in records:
        await agent_memory.save_tool_usage(
            question=record["question"],
            tool_name="run_sql",
            args={"sql": record["sql"]},
            context=context,
            success=True,
            metadata={"notes": record.get("notes"), "source": "memory_seed"},
        )
        seeded_count += 1

    schema_notes = (
        "Clinic analytics schema: patients, doctors, appointments, treatments, invoices. "
        "Use joins through appointments for doctor-level operational questions and treatments "
        "for doctor/department revenue and duration calculations."
    )
    await agent_memory.save_text_memory(schema_notes, context)
    return seeded_count


def create_tool_registry() -> ToolRegistry:
    tools = ToolRegistry()
    db_tool = RunSqlTool(sql_runner=SafeSqliteRunner(database_path=str(DB_PATH)))
    tools.register_local_tool(db_tool, access_groups=["admin", "user"])
    tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["admin"])
    tools.register_local_tool(
        SearchSavedCorrectToolUsesTool(), access_groups=["admin", "user"]
    )
    tools.register_local_tool(SaveTextMemoryTool(), access_groups=["admin", "user"])
    tools.register_local_tool(VisualizeDataTool(), access_groups=["admin", "user"])
    return tools


def run_async_safely(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover
            error["value"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


def build_agent(*, allow_missing_api_key: bool = True) -> tuple[Agent | None, DemoAgentMemory, dict[str, Any]]:
    load_dotenv()
    agent_memory = DemoAgentMemory(max_items=2000)
    seeded_count = run_async_safely(seed_agent_memory(agent_memory))

    api_key = os.getenv("GOOGLE_API_KEY")
    metadata = {
        "provider": "Gemini",
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "seeded_items": seeded_count,
        "configured": bool(api_key),
    }

    if not api_key:
        if allow_missing_api_key:
            LOGGER.warning("GOOGLE_API_KEY not set; Vanna agent endpoints will be disabled.")
            return None, agent_memory, metadata
        raise RuntimeError("GOOGLE_API_KEY is required to initialize GeminiLlmService.")

    llm = GeminiLlmService(model=metadata["model"], api_key=api_key, temperature=0.1)
    agent = Agent(
        llm_service=llm,
        tool_registry=create_tool_registry(),
        user_resolver=DefaultUserResolver(),
        agent_memory=agent_memory,
        config=AgentConfig(max_tool_iterations=6, temperature=0.1, stream_responses=True),
    )
    return agent, agent_memory, metadata
