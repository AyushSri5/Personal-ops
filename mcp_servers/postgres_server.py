"""Postgres MCP Server — full read/write SQL access.

Tools:
- list_tables()
- describe_table(table)
- run_query(sql, limit)          ← SELECT only
- execute(sql)                   ← INSERT / UPDATE / DELETE
- get_table_sample(table, limit)
- get_db_stats()
- create_meeting_note(title, date, attendees, body)
- create_task(title, description, assignee, due_date)
- create_bug(title, description, severity, repo)
- update_task_status(task_id, status)
- update_bug_status(bug_id, status)
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date as Date
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncpg
from fastmcp import FastMCP
from config.settings import get_settings

settings = get_settings()

mcp = FastMCP(
    name="postgres",
    instructions=(
        f"Full read/write access to PostgreSQL '{settings.postgres_db}'. "
        "Use run_query() for SELECT. Use execute() or dedicated tools for INSERT/UPDATE/DELETE."
    ),
)

# ── Connection ────────────────────────────────────────────────────────────────

async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
        timeout=10,
    )


def _run_async(coro):
    """Run a coroutine from sync context safely."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result(timeout=30)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _format(records: list, max_rows: int = 50) -> str:
    if not records:
        return "(no rows returned)"
    cols = list(records[0].keys())
    w = 22
    header = " | ".join(f"{c:<{w}}" for c in cols)
    sep    = "-+-".join("-" * w for _ in cols)
    lines  = [header, sep]
    for row in records[:max_rows]:
        lines.append(" | ".join(f"{str(row[c]):<{w}}" for c in cols))
    if len(records) > max_rows:
        lines.append(f"... {len(records) - max_rows} more rows truncated")
    return "\n".join(lines)


# ── Read tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_tables() -> str:
    """List all tables in the connected PostgreSQL database."""
    async def _q():
        conn = await _connect()
        try:
            return await conn.fetch(
                """SELECT table_name,
                          pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
                   FROM information_schema.tables
                   WHERE table_schema = 'public'
                   ORDER BY table_name"""
            )
        finally:
            await conn.close()
    rows = _run_async(_q())
    lines = [f"Tables in '{settings.postgres_db}':", ""]
    for r in rows:
        lines.append(f"  📋 {r['table_name']:<30} {r['size']}")
    return "\n".join(lines)


@mcp.tool()
def describe_table(table: str) -> str:
    """Show columns, types and constraints for a table.

    Args:
        table: Table name
    """
    async def _q():
        conn = await _connect()
        try:
            cols = await conn.fetch(
                """SELECT column_name, data_type, character_maximum_length,
                          is_nullable, column_default
                   FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = $1
                   ORDER BY ordinal_position""",
                table,
            )
            constraints = await conn.fetch(
                """SELECT constraint_type, constraint_name
                   FROM information_schema.table_constraints
                   WHERE table_schema = 'public' AND table_name = $1""",
                table,
            )
            return cols, constraints
        finally:
            await conn.close()
    cols, constraints = _run_async(_q())
    if not cols:
        return f"Table '{table}' not found."
    lines = [f"Table: {table}", ""]
    lines.append(f"  {'Column':<25} {'Type':<25} {'Nullable':<10} Default")
    lines.append(f"  {'-'*25} {'-'*25} {'-'*10} {'-'*20}")
    for c in cols:
        dt = c["data_type"]
        if c["character_maximum_length"]:
            dt += f"({c['character_maximum_length']})"
        lines.append(
            f"  {c['column_name']:<25} {dt:<25} "
            f"{'YES' if c['is_nullable']=='YES' else 'NO':<10} "
            f"{str(c['column_default'] or '')}"
        )
    if constraints:
        lines += ["", "Constraints:"]
        for ct in constraints:
            lines.append(f"  {ct['constraint_type']}: {ct['constraint_name']}")
    return "\n".join(lines)


@mcp.tool()
def run_query(sql: str, limit: int = 50) -> str:
    """Execute a SELECT query and return results as a formatted table.

    Args:
        sql: A valid SELECT statement
        limit: Max rows to return (default 50)
    """
    first = sql.strip().split()[0].upper()
    if first != "SELECT":
        return "❌ run_query() is for SELECT only. Use execute() for INSERT/UPDATE/DELETE."
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip(";") + f" LIMIT {min(limit, 500)}"

    async def _q():
        conn = await _connect()
        try:
            return list(await conn.fetch(sql))
        finally:
            await conn.close()
    rows = _run_async(_q())
    return f"Query: {sql}\n\n" + _format(rows, max_rows=min(limit, 500))


@mcp.tool()
def get_table_sample(table: str, limit: int = 10) -> str:
    """Preview the first N rows from a table.

    Args:
        table: Table name
        limit: Number of rows
    """
    return run_query(f"SELECT * FROM {table}", limit=limit)


@mcp.tool()
def get_db_stats() -> str:
    """Get database version, size, and connection count."""
    async def _q():
        conn = await _connect()
        try:
            version = await conn.fetchval("SELECT version()")
            db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
            conns   = await conn.fetchval("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            return version, db_size, conns
        finally:
            await conn.close()
    version, db_size, conns = _run_async(_q())
    return (
        f"Database:    {settings.postgres_db}\n"
        f"Host:        {settings.postgres_host}:{settings.postgres_port}\n"
        f"Size:        {db_size}\n"
        f"Connections: {conns}\n"
        f"Version:     {version}"
    )


# ── Write tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def execute(sql: str) -> str:
    """Execute an INSERT, UPDATE, or DELETE SQL statement.

    Args:
        sql: A valid INSERT / UPDATE / DELETE statement
    """
    first = sql.strip().split()[0].upper()
    allowed = {"INSERT", "UPDATE", "DELETE"}
    if first not in allowed:
        return f"❌ execute() only allows INSERT / UPDATE / DELETE. Got: {first}. Use run_query() for SELECT."

    async def _q():
        conn = await _connect()
        try:
            result = await conn.execute(sql)
            return result
        finally:
            await conn.close()
    result = _run_async(_q())
    return f"✓ Executed successfully. Result: {result}"


@mcp.tool()
def create_meeting_note(
    title: str,
    date: str,
    body: str,
    attendees: str = "",
) -> str:
    """Store a meeting note in the meeting_notes table.

    Args:
        title: Title of the meeting
        date: Date in YYYY-MM-DD format (e.g. '2025-06-24')
        body: Full meeting notes content
        attendees: Comma-separated list of attendees (e.g. 'Alice, Bob, Carol')
    """
    attendees_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else []

    async def _q():
        conn = await _connect()
        try:
            row = await conn.fetchrow(
                """INSERT INTO meeting_notes (title, date, attendees, body)
                   VALUES ($1, $2, $3, $4)
                   RETURNING id, title, date""",
                title,
                Date.fromisoformat(date),
                attendees_list,
                body,
            )
            return row
        finally:
            await conn.close()
    row = _run_async(_q())
    return (
        f"✓ Meeting note saved!\n"
        f"  ID:    {row['id']}\n"
        f"  Title: {row['title']}\n"
        f"  Date:  {row['date']}"
    )


@mcp.tool()
def create_task(
    title: str,
    description: str = "",
    assignee: str = "",
    due_date: str = "",
) -> str:
    """Create a new task in the tasks table.

    Args:
        title: Task title
        description: Task description
        assignee: Who is responsible
        due_date: Due date in YYYY-MM-DD format (optional)
    """
    async def _q():
        conn = await _connect()
        try:
            due = Date.fromisoformat(due_date) if due_date else None
            row = await conn.fetchrow(
                """INSERT INTO tasks (title, description, assignee, due_date, status)
                   VALUES ($1, $2, $3, $4, 'todo')
                   RETURNING id, title, status""",
                title, description or None, assignee or None, due,
            )
            return row
        finally:
            await conn.close()
    row = _run_async(_q())
    return (
        f"✓ Task created!\n"
        f"  ID:     {row['id']}\n"
        f"  Title:  {row['title']}\n"
        f"  Status: {row['status']}"
    )


@mcp.tool()
def create_bug(
    title: str,
    description: str = "",
    severity: str = "medium",
    repo: str = "",
) -> str:
    """Log a new bug in the bugs table.

    Args:
        title: Bug title
        description: Detailed description
        severity: 'critical', 'high', 'medium', or 'low' (default: medium)
        repo: Repository name this bug belongs to
    """
    valid_severities = {"critical", "high", "medium", "low"}
    if severity not in valid_severities:
        return f"❌ Invalid severity '{severity}'. Must be one of: {', '.join(valid_severities)}"

    async def _q():
        conn = await _connect()
        try:
            row = await conn.fetchrow(
                """INSERT INTO bugs (title, description, severity, status, repo)
                   VALUES ($1, $2, $3, 'open', $4)
                   RETURNING id, title, severity, status""",
                title, description or None, severity, repo or None,
            )
            return row
        finally:
            await conn.close()
    row = _run_async(_q())
    return (
        f"✓ Bug logged!\n"
        f"  ID:       {row['id']}\n"
        f"  Title:    {row['title']}\n"
        f"  Severity: {row['severity']}\n"
        f"  Status:   {row['status']}"
    )


@mcp.tool()
def update_task_status(task_id: int, status: str) -> str:
    """Update the status of a task.

    Args:
        task_id: Task ID (from list_tables or run_query)
        status: New status — 'todo', 'in_progress', 'done', or 'cancelled'
    """
    valid = {"todo", "in_progress", "done", "cancelled"}
    if status not in valid:
        return f"❌ Invalid status '{status}'. Must be one of: {', '.join(valid)}"

    async def _q():
        conn = await _connect()
        try:
            row = await conn.fetchrow(
                "UPDATE tasks SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING id, title, status"
                if "updated_at" in [c["column_name"] for c in await conn.fetch(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='tasks'"
                )]
                else "UPDATE tasks SET status = $1 WHERE id = $2 RETURNING id, title, status",
                status, task_id,
            )
            return row
        finally:
            await conn.close()
    row = _run_async(_q())
    if not row:
        return f"❌ No task found with ID {task_id}"
    return f"✓ Task #{row['id']} '{row['title']}' → {row['status']}"


@mcp.tool()
def update_bug_status(bug_id: int, status: str) -> str:
    """Update the status of a bug.

    Args:
        bug_id: Bug ID
        status: New status — 'open', 'in_progress', 'resolved', or 'closed'
    """
    valid = {"open", "in_progress", "resolved", "closed"}
    if status not in valid:
        return f"❌ Invalid status '{status}'. Must be one of: {', '.join(valid)}"

    async def _q():
        conn = await _connect()
        try:
            row = await conn.fetchrow(
                "UPDATE bugs SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING id, title, status",
                status, bug_id,
            )
            return row
        finally:
            await conn.close()
    row = _run_async(_q())
    if not row:
        return f"❌ No bug found with ID {bug_id}"
    return f"✓ Bug #{row['id']} '{row['title']}' → {row['status']}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
