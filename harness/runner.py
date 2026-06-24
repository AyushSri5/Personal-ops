"""
Harness runner — executes tasks against the agent and collects metrics.

Features:
- Sequential or bounded-concurrent execution
- Per-task timeout
- Tool-call interception via astream_events
- Live progress display via Rich
- Graceful skip for tasks that need missing credentials
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

from agent.graph import _build_agent
from harness.metrics import HarnessReport, TaskResult
from harness.tasks import Task

console = Console()

# ── Settings ──────────────────────────────────────────────────────────────────
DEFAULT_TIMEOUT_S = 120       # per-task timeout
DEFAULT_CONCURRENCY = 1       # sequential by default (avoids rate limits)


# ── Tool-call interceptor ─────────────────────────────────────────────────────

async def _run_task_with_tracing(
    agent,
    task: Task,
    timeout_s: int,
) -> tuple[str, list[str]]:
    """
    Run one task through the agent, capture the response and which tools
    were actually invoked. Returns (response_text, tools_called).
    """
    messages = [("user", task.prompt)]
    tools_called: list[str] = []
    response_parts: list[str] = []

    async def _stream():
        async for event in agent.astream_events(
            {"messages": messages},
            version="v2",
            config={"recursion_limit": 25},
        ):
            kind = event.get("event", "")
            if kind == "on_tool_start":
                tool_name = event.get("name", "")
                if tool_name:
                    tools_called.append(tool_name)
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    response_parts.append(chunk.content)

    await asyncio.wait_for(_stream(), timeout=timeout_s)
    return "".join(response_parts), tools_called


# ── Single task runner ────────────────────────────────────────────────────────

async def run_task(
    agent,
    task: Task,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    skip_categories: Optional[set[str]] = None,
) -> TaskResult:
    """Execute one task and return its TaskResult."""
    if skip_categories and task.category in skip_categories:
        return TaskResult(
            task=task,
            success=True,
            response="",
            tools_called=[],
            latency_ms=0.0,
            skipped=True,
        )

    t0 = time.perf_counter()
    try:
        response, tools_called = await _run_task_with_tracing(agent, task, timeout_s)
        latency_ms = (time.perf_counter() - t0) * 1000
        return TaskResult(
            task=task,
            success=True,
            response=response,
            tools_called=tools_called,
            latency_ms=latency_ms,
        )
    except asyncio.TimeoutError:
        latency_ms = (time.perf_counter() - t0) * 1000
        return TaskResult(
            task=task,
            success=False,
            response="",
            tools_called=[],
            latency_ms=latency_ms,
            error=f"Timed out after {timeout_s}s",
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        return TaskResult(
            task=task,
            success=False,
            response="",
            tools_called=[],
            latency_ms=latency_ms,
            error=str(exc),
        )


# ── Harness runner ────────────────────────────────────────────────────────────

async def run_harness(
    tasks: list[Task],
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    skip_categories: Optional[set[str]] = None,
) -> HarnessReport:
    """
    Run all tasks through the agent and return a HarnessReport.

    Args:
        tasks: List of Task objects to run
        concurrency: Max simultaneous tasks (default 1 = sequential)
        timeout_s: Per-task timeout in seconds
        skip_categories: Category names to skip (e.g. {'notion'} if no API key)
    """
    started_at = datetime.now()
    results: list[TaskResult] = []

    # Build agent once — reused across all tasks
    console.print("\n[bold cyan]⚙  Building agent and connecting to MCP servers...[/bold cyan]")
    agent = await _build_agent()
    console.print("[bold green]✓  Agent ready[/bold green]\n")

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(task: Task) -> TaskResult:
        async with semaphore:
            result = await run_task(agent, task, timeout_s, skip_categories)
            return result

    with Live(progress, console=console, refresh_per_second=10):
        pg_task = progress.add_task(
            f"Running {len(tasks)} tasks",
            total=len(tasks),
        )

        if concurrency == 1:
            # Sequential — update progress after each task
            for task in tasks:
                progress.update(
                    pg_task,
                    description=f"[bold blue]{task.id}[/bold blue] {task.prompt[:50]}...",
                )
                result = await run_task(agent, task, timeout_s, skip_categories)
                results.append(result)
                progress.advance(pg_task)
        else:
            # Concurrent with semaphore
            coros = [_bounded(t) for t in tasks]
            for coro in asyncio.as_completed(coros):
                result = await coro
                results.append(result)
                progress.advance(pg_task)

    finished_at = datetime.now()

    # Preserve original task order
    id_to_result = {r.task.id: r for r in results}
    ordered = [id_to_result[t.id] for t in tasks if t.id in id_to_result]

    return HarnessReport(
        results=ordered,
        started_at=started_at,
        finished_at=finished_at,
    )
