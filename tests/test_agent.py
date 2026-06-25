"""
Unit tests for Personal Ops Agent.

These tests run without any API keys or running services.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Config / Settings ─────────────────────────────────────────────────────────

def test_settings_load_with_defaults(monkeypatch):
    """Settings should load with env vars, no .env file needed in CI."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("LOCAL_FILES_ROOT", "/tmp")

    # Clear LRU cache so fresh instance is created
    from config.settings import get_settings
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.openai_api_key == "sk-test-dummy"
    assert settings.agent_model == "gpt-4o-mini"
    assert settings.agent_max_iterations == 25
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432

    get_settings.cache_clear()


def test_settings_postgres_dsn(monkeypatch):
    """DSN property should format correctly."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("LOCAL_FILES_ROOT", "/tmp")

    from config.settings import get_settings
    get_settings.cache_clear()
    s = get_settings()

    assert "ops_user" in s.postgres_dsn
    assert "localhost" in s.postgres_dsn
    assert "ops_db" in s.postgres_dsn
    get_settings.cache_clear()


# ── Harness task definitions ──────────────────────────────────────────────────

def test_all_tasks_have_required_fields():
    """Every task must have id, category, difficulty, prompt, expected_tools."""
    from harness.tasks import ALL_TASKS
    for task in ALL_TASKS:
        assert task.id,             f"Task missing id: {task}"
        assert task.category,       f"Task {task.id} missing category"
        assert task.difficulty in ("easy", "medium", "hard"), \
            f"Task {task.id} has invalid difficulty: {task.difficulty}"
        assert task.prompt,         f"Task {task.id} missing prompt"
        assert task.expected_tools, f"Task {task.id} has no expected_tools"


def test_task_ids_are_unique():
    """No two tasks should share the same ID."""
    from harness.tasks import ALL_TASKS
    ids = [t.id for t in ALL_TASKS]
    assert len(ids) == len(set(ids)), "Duplicate task IDs found"


def test_task_count():
    """Harness should have at least 30 tasks."""
    from harness.tasks import ALL_TASKS
    assert len(ALL_TASKS) >= 30, f"Only {len(ALL_TASKS)} tasks defined — need at least 30"


def test_tasks_by_category_complete():
    """All 6 categories should be present."""
    from harness.tasks import TASKS_BY_CATEGORY
    expected_cats = {"filesystem", "github", "postgres_read", "postgres_write", "notion", "cross_tool"}
    assert expected_cats == set(TASKS_BY_CATEGORY.keys())


def test_tasks_by_id_lookup():
    """TASKS_BY_ID should allow fast lookup by task ID."""
    from harness.tasks import TASKS_BY_ID, ALL_TASKS
    assert len(TASKS_BY_ID) == len(ALL_TASKS)
    for task in ALL_TASKS:
        assert TASKS_BY_ID[task.id] is task


# ── Harness metrics ───────────────────────────────────────────────────────────

def test_task_result_tool_hit_rate_full_match():
    """Tool hit rate should be 1.0 when all expected tools were called."""
    from harness.tasks import Task
    from harness.metrics import TaskResult
    task = Task(
        id="test-01", category="filesystem", difficulty="easy",
        prompt="test", expected_tools=["read_file", "list_directory"],
        description="test",
    )
    result = TaskResult(
        task=task, success=True, response="ok",
        tools_called=["read_file", "list_directory"], latency_ms=100.0
    )
    assert result.tool_hit_rate == 1.0
    assert result.tools_matched is True
    assert result.status_label == "PASS"


def test_task_result_tool_hit_rate_partial():
    """Tool hit rate should be 0.5 when half expected tools called."""
    from harness.tasks import Task
    from harness.metrics import TaskResult
    task = Task(
        id="test-02", category="github", difficulty="medium",
        prompt="test", expected_tools=["search_notion", "get_page"],
        description="test",
    )
    result = TaskResult(
        task=task, success=True, response="ok",
        tools_called=["search_notion"], latency_ms=200.0
    )
    assert result.tool_hit_rate == 0.5
    assert result.tools_matched is False
    assert result.status_label == "PARTIAL"


def test_task_result_failure():
    """Failed tasks should report FAIL status."""
    from harness.tasks import Task
    from harness.metrics import TaskResult
    task = Task(
        id="test-03", category="notion", difficulty="hard",
        prompt="test", expected_tools=["get_page"],
        description="test",
    )
    result = TaskResult(
        task=task, success=False, response="",
        tools_called=[], latency_ms=5000.0, error="TimeoutError"
    )
    assert result.status_label == "FAIL"
    assert result.status_emoji == "❌"


def test_harness_report_stats():
    """HarnessReport aggregation stats should be correct."""
    from datetime import datetime, timedelta
    from harness.tasks import Task
    from harness.metrics import TaskResult, HarnessReport

    def _task(tid: str) -> Task:
        return Task(id=tid, category="filesystem", difficulty="easy",
                    prompt="p", expected_tools=["read_file"], description="d")

    results = [
        TaskResult(task=_task("t1"), success=True,  response="ok", tools_called=["read_file"],  latency_ms=100),
        TaskResult(task=_task("t2"), success=True,  response="ok", tools_called=["write_file"], latency_ms=200),  # partial
        TaskResult(task=_task("t3"), success=False, response="",   tools_called=[],             latency_ms=500, error="err"),
    ]
    now = datetime.now()
    report = HarnessReport(results=results, started_at=now, finished_at=now + timedelta(seconds=5))

    assert report.total   == 3
    assert report.passed  == 1
    assert report.partial == 1
    assert report.failed  == 1
    assert report.pass_rate   == pytest.approx(33.33, abs=0.1)
    assert report.success_rate == pytest.approx(66.67, abs=0.1)


# ── Filesystem MCP server (no I/O, just imports + path safety) ────────────────

def test_filesystem_safe_path_rejects_traversal(tmp_path, monkeypatch):
    """Path traversal outside ROOT should raise PermissionError."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("LOCAL_FILES_ROOT", str(tmp_path))

    from config.settings import get_settings
    get_settings.cache_clear()

    import importlib
    import mcp_servers.filesystem_server as fs_mod
    importlib.reload(fs_mod)

    import pytest
    with pytest.raises(PermissionError):
        fs_mod._safe("../../etc/passwd")

    get_settings.cache_clear()


# ── Postgres server safety ────────────────────────────────────────────────────

def test_postgres_run_query_rejects_insert(monkeypatch):
    """run_query must block INSERT statements."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("LOCAL_FILES_ROOT", "/tmp")

    import importlib
    import mcp_servers.postgres_server as pg_mod
    importlib.reload(pg_mod)

    result = pg_mod.run_query("INSERT INTO bugs VALUES (1, 'x')")
    assert "Only SELECT" in result or "❌" in result


def test_postgres_execute_rejects_select(monkeypatch):
    """execute() must block SELECT statements."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("LOCAL_FILES_ROOT", "/tmp")

    import importlib
    import mcp_servers.postgres_server as pg_mod
    importlib.reload(pg_mod)

    result = pg_mod.execute("SELECT * FROM bugs")
    assert "❌" in result


import pytest  # noqa: E402 — placed at bottom intentionally
