"""
Harness metrics — result data model and scoring logic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from harness.tasks import Task


@dataclass
class TaskResult:
    """Result of running a single harness task."""
    task: Task
    success: bool                          # True = no exception raised
    response: str                          # Agent's final text response
    tools_called: list[str]               # Tools actually invoked
    latency_ms: float                      # Wall-clock time in milliseconds
    error: Optional[str] = None           # Exception message if failed
    skipped: bool = False                 # True if task was intentionally skipped

    @property
    def tool_hit_rate(self) -> float:
        """Fraction of expected tools that were actually called (0.0–1.0)."""
        if not self.task.expected_tools:
            return 1.0
        called = set(self.tools_called)
        expected = set(self.task.expected_tools)
        return len(called & expected) / len(expected)

    @property
    def tools_matched(self) -> bool:
        """True if ALL expected tools were called."""
        return self.tool_hit_rate == 1.0

    @property
    def status_emoji(self) -> str:
        if self.skipped:
            return "⏭️"
        if self.success and self.tools_matched:
            return "✅"
        if self.success and not self.tools_matched:
            return "⚠️"
        return "❌"

    @property
    def status_label(self) -> str:
        if self.skipped:
            return "SKIPPED"
        if self.success and self.tools_matched:
            return "PASS"
        if self.success and not self.tools_matched:
            return "PARTIAL"
        return "FAIL"


@dataclass
class HarnessReport:
    """Aggregated results from a full harness run."""
    results: list[TaskResult]
    started_at: datetime
    finished_at: datetime

    # ── Computed stats ──────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.success and r.tools_matched and not r.skipped)

    @property
    def partial(self) -> int:
        return sum(1 for r in self.results if r.success and not r.tools_matched and not r.skipped)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success and not r.skipped)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def pass_rate(self) -> float:
        active = self.total - self.skipped
        return (self.passed / active * 100) if active else 0.0

    @property
    def success_rate(self) -> float:
        """Pass + Partial (agent responded without error)."""
        active = self.total - self.skipped
        return ((self.passed + self.partial) / active * 100) if active else 0.0

    @property
    def avg_latency_ms(self) -> float:
        active = [r for r in self.results if not r.skipped]
        return sum(r.latency_ms for r in active) / len(active) if active else 0.0

    @property
    def total_duration_s(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    def by_category(self) -> dict[str, list[TaskResult]]:
        cats: dict[str, list[TaskResult]] = {}
        for r in self.results:
            cats.setdefault(r.task.category, []).append(r)
        return cats

    def by_difficulty(self) -> dict[str, list[TaskResult]]:
        diffs: dict[str, list[TaskResult]] = {}
        for r in self.results:
            diffs.setdefault(r.task.difficulty, []).append(r)
        return diffs

    # ── Serialisation ───────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "partial": self.partial,
                "failed": self.failed,
                "skipped": self.skipped,
                "pass_rate_pct": round(self.pass_rate, 1),
                "success_rate_pct": round(self.success_rate, 1),
                "avg_latency_ms": round(self.avg_latency_ms, 0),
                "total_duration_s": round(self.total_duration_s, 1),
                "started_at": self.started_at.isoformat(),
                "finished_at": self.finished_at.isoformat(),
            },
            "results": [
                {
                    "id": r.task.id,
                    "category": r.task.category,
                    "difficulty": r.task.difficulty,
                    "status": r.status_label,
                    "tools_called": r.tools_called,
                    "expected_tools": r.task.expected_tools,
                    "tool_hit_rate": round(r.tool_hit_rate, 2),
                    "latency_ms": round(r.latency_ms, 0),
                    "error": r.error,
                    "response_preview": r.response[:300] if r.response else None,
                }
                for r in self.results
            ],
        }

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
