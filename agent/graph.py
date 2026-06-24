"""
Personal Ops — LangGraph ReAct Agent

Builds a create_react_agent graph that connects to all four MCP servers
(filesystem, github, postgres, notion) via MultiServerMCPClient.

Usage:
    # One-shot
    response = asyncio.run(run_once("find the latest bug"))

    # Streaming
    async for chunk in stream_once("summarize this repo"):
        print(chunk, end="")

    # As async context manager (reuse connections)
    async with await build_graph() as agent:
        result = await agent.ainvoke({"messages": [("user", "...")]})
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent.prompts import SYSTEM_PROMPT
from config.settings import get_settings

settings = get_settings()


# ── MCP server configuration ──────────────────────────────────────────────────

def _mcp_config() -> dict:
    py = sys.executable
    servers = PROJECT_ROOT / "mcp_servers"

    def _stdio(script: str) -> dict:
        return {
            "command": py,
            "args": [str(servers / script)],
            "transport": "stdio",
            "env": dict(os.environ),
        }

    return {
        "filesystem": _stdio("filesystem_server.py"),
        "github":     _stdio("github_server.py"),
        "postgres":   _stdio("postgres_server.py"),
        "notion":     _stdio("notion_server.py"),
    }


# ── Graph builder ─────────────────────────────────────────────────────────────

async def _build_agent():
    """
    Create and return a compiled ReAct agent with all MCP tools loaded.
    Uses MultiServerMCPClient with await client.get_tools() (v0.1.0+ API).
    """
    client = MultiServerMCPClient(_mcp_config())
    tools = await client.get_tools()

    # print(f"Tools present: {tools}")

    llm = ChatOpenAI(
        model=settings.agent_model,
        temperature=settings.agent_temperature,
        api_key=settings.openai_api_key,
    )
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def run_once(user_message: str, history: list | None = None) -> str:
    """Run the agent and return the final text response.

    Args:
        user_message: User's natural-language request
        history: Optional prior (role, message) pairs for context
    """
    messages = list(history or []) + [("user", user_message)]
    agent = await _build_agent()
    result = await agent.ainvoke(
        {"messages": messages},
        config={"recursion_limit": settings.agent_max_iterations},
    )
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.content and msg.type == "ai":
            return msg.content
    return "(no response)"


async def stream_once(user_message: str, history: list | None = None):
    """Stream the agent's response as text chunks.

    Yields:
        str chunks of the response (tool calls annotated inline)
    """
    messages = list(history or []) + [("user", user_message)]
    agent = await _build_agent()
    async for event in agent.astream_events(
        {"messages": messages},
        version="v2",
        config={"recursion_limit": settings.agent_max_iterations},
    ):
        kind = event.get("event", "")
        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield chunk.content
        elif kind == "on_tool_start":
            name = event.get("name", "")
            inp = json.dumps(event.get("data", {}).get("input", {}), ensure_ascii=False)
            yield f"\n\n🔧 **{name}**({inp[:120]})\n"
        elif kind == "on_tool_end":
            yield "\n"
