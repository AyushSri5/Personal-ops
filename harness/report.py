"""
Harness report renderer — rich terminal tables + markdown file output.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from harness.metrics import HarnessReport

console = Console()

# ── Colour helpers ────────────────────────────────────────────────────────────

_STATUS_STYLE = {
    "PASS":    "bold green",
    "PARTIAL": "bold yellow",
    "FAIL":    "bold red",
    "SKIPPED": "dim",
}
_DIFF_STYLE = {
    "easy":   "green",
    "medium": "yellow",
    "hard":   "red",
}
_CAT_EMOJI = {
    "filesystem":     "📁",
    "github":         "🐙",
    "postgres_read":  "🗄️ R",
    "postgres_write": "🗄️ W",
    "notion":         "📝",
    "cross_tool":     "🔀",
}


def _pct_color(pct: float) -> str:
    if pct >= 80:
        return "bold green"
    if pct >= 50:
        return "bold yellow"
    return "bold red"


# ── Summary panel ─────────────────────────────────────────────────────────────

def print_summary(report: HarnessReport) -> None:
    console.print()
    console.print(Rule("[bold white]⚡ Harness Run Complete[/bold white]", style="cyan"))
    console.print()

    # ── Top-line stats ────────────────────────────────────────────────────
    stats = Table.grid(expand=False, padding=(0, 3))
    stats.add_column(style="dim")
    stats.add_column()

    stats.add_row("Total tasks",     f"[bold white]{report.total}[/bold white]")
    stats.add_row("✅ Passed",        f"[bold green]{report.passed}[/bold green]")
    stats.add_row("⚠️  Partial",       f"[bold yellow]{report.partial}[/bold yellow]")
    stats.add_row("❌ Failed",         f"[bold red]{report.failed}[/bold red]")
    stats.add_row("⏭️  Skipped",       f"[dim]{report.skipped}[/dim]")
    stats.add_row("Pass rate",        f"[{_pct_color(report.pass_rate)}]{report.pass_rate:.1f}%[/]")
    stats.add_row("Response rate",   f"[{_pct_color(report.success_rate)}]{report.success_rate:.1f}%[/]")
    stats.add_row("Avg latency",      f"[cyan]{report.avg_latency_ms:,.0f} ms[/cyan]")
    stats.add_row("Total duration",   f"[cyan]{report.total_duration_s:.1f} s[/cyan]")

    console.print(Panel(stats, title="[bold cyan]📊 Summary[/bold cyan]", border_style="cyan"))


# ── Per-category breakdown ─────────────────────────────────────────────────────

def print_category_breakdown(report: HarnessReport) -> None:
    console.print()
    console.print(Rule("[bold white]📂 Results by Category[/bold white]", style="blue"))
    console.print()

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
    table.add_column("Category",    style="cyan", width=16)
    table.add_column("Tasks",       justify="center", width=7)
    table.add_column("✅ Pass",      justify="center", width=8)
    table.add_column("⚠️  Partial",  justify="center", width=9)
    table.add_column("❌ Fail",      justify="center", width=8)
    table.add_column("Pass %",      justify="center", width=8)
    table.add_column("Avg ms",      justify="right",  width=9)

    for cat, results in report.by_category().items():
        active = [r for r in results if not r.skipped]
        p  = sum(1 for r in active if r.status_label == "PASS")
        pt = sum(1 for r in active if r.status_label == "PARTIAL")
        f  = sum(1 for r in active if r.status_label == "FAIL")
        pct = (p / len(active) * 100) if active else 0.0
        avg = sum(r.latency_ms for r in active) / len(active) if active else 0
        emoji = _CAT_EMOJI.get(cat, "")
        table.add_row(
            f"{emoji} {cat}",
            str(len(results)),
            f"[green]{p}[/green]",
            f"[yellow]{pt}[/yellow]",
            f"[red]{f}[/red]",
            f"[{_pct_color(pct)}]{pct:.0f}%[/]",
            f"{avg:,.0f}",
        )

    console.print(table)


# ── Per-difficulty breakdown ──────────────────────────────────────────────────

def print_difficulty_breakdown(report: HarnessReport) -> None:
    console.print()
    console.print(Rule("[bold white]🎯 Results by Difficulty[/bold white]", style="blue"))
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold white")
    table.add_column("Difficulty", width=10)
    table.add_column("Tasks",     justify="center", width=7)
    table.add_column("Pass %",    justify="center", width=8)
    table.add_column("Avg ms",    justify="right",  width=9)

    for diff in ["easy", "medium", "hard"]:
        results = report.by_difficulty().get(diff, [])
        if not results:
            continue
        active = [r for r in results if not r.skipped]
        p = sum(1 for r in active if r.status_label == "PASS")
        pct = (p / len(active) * 100) if active else 0.0
        avg = sum(r.latency_ms for r in active) / len(active) if active else 0
        table.add_row(
            f"[{_DIFF_STYLE[diff]}]{diff.capitalize()}[/]",
            str(len(results)),
            f"[{_pct_color(pct)}]{pct:.0f}%[/]",
            f"{avg:,.0f}",
        )

    console.print(table)


# ── Full results table ────────────────────────────────────────────────────────

def print_results_table(report: HarnessReport) -> None:
    console.print()
    console.print(Rule("[bold white]📋 All Task Results[/bold white]", style="blue"))
    console.print()

    table = Table(box=box.MINIMAL_DOUBLE_HEAD, show_header=True, header_style="bold white")
    table.add_column("ID",          style="dim cyan", width=10)
    table.add_column("Status",      justify="center", width=9)
    table.add_column("Diff",        width=8)
    table.add_column("Category",    width=14)
    table.add_column("Tools Called",               width=30)
    table.add_column("Hit %",       justify="center", width=7)
    table.add_column("ms",          justify="right",  width=7)
    table.add_column("Error / Note",               width=30)

    for r in report.results:
        tools_str = ", ".join(r.tools_called[:4]) + ("…" if len(r.tools_called) > 4 else "")
        hit_pct   = f"{r.tool_hit_rate * 100:.0f}%"
        error_str = (r.error or "")[:40] if r.error else ""
        status_style = _STATUS_STYLE.get(r.status_label, "")

        table.add_row(
            r.task.id,
            f"[{status_style}]{r.status_emoji} {r.status_label}[/]",
            f"[{_DIFF_STYLE.get(r.task.difficulty, '')}]{r.task.difficulty}[/]",
            r.task.category,
            tools_str or "[dim](none)[/dim]",
            f"[{_pct_color(r.tool_hit_rate * 100)}]{hit_pct}[/]",
            f"{r.latency_ms:,.0f}" if not r.skipped else "—",
            f"[dim red]{error_str}[/dim red]" if error_str else "",
        )

    console.print(table)


# ── Failures detail ───────────────────────────────────────────────────────────

def print_failures(report: HarnessReport) -> None:
    failures = [r for r in report.results if r.status_label == "FAIL"]
    if not failures:
        console.print("\n[bold green]🎉 No failures![/bold green]")
        return

    console.print()
    console.print(Rule(f"[bold red]❌ Failures ({len(failures)})[/bold red]", style="red"))
    for r in failures:
        console.print(f"\n  [bold red]{r.task.id}[/bold red]  {r.task.prompt[:70]}")
        console.print(f"  [dim]Error:[/dim] {r.error}")


# ── Markdown report ───────────────────────────────────────────────────────────

def save_markdown_report(report: HarnessReport, path: Path) -> None:
    lines = [
        "# ⚡ Personal Ops — Harness Report",
        "",
        f"**Run started:** {report.started_at.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Duration:** {report.total_duration_s:.1f}s",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total tasks | {report.total} |",
        f"| ✅ Passed | {report.passed} |",
        f"| ⚠️ Partial | {report.partial} |",
        f"| ❌ Failed | {report.failed} |",
        f"| ⏭️ Skipped | {report.skipped} |",
        f"| Pass rate | {report.pass_rate:.1f}% |",
        f"| Response rate | {report.success_rate:.1f}% |",
        f"| Avg latency | {report.avg_latency_ms:,.0f} ms |",
        "",
        "## Results by Category",
        "",
        "| Category | Tasks | Pass | Partial | Fail | Pass % |",
        "|---|---|---|---|---|---|",
    ]

    for cat, results in report.by_category().items():
        active = [r for r in results if not r.skipped]
        p  = sum(1 for r in active if r.status_label == "PASS")
        pt = sum(1 for r in active if r.status_label == "PARTIAL")
        f  = sum(1 for r in active if r.status_label == "FAIL")
        pct = (p / len(active) * 100) if active else 0.0
        lines.append(f"| {cat} | {len(results)} | {p} | {pt} | {f} | {pct:.0f}% |")

    lines += ["", "## All Results", "", "| ID | Status | Difficulty | Category | Tools Called | Hit% | ms | Error |", "|---|---|---|---|---|---|---|---|"]

    for r in report.results:
        tools = ", ".join(r.tools_called) or "—"
        lines.append(
            f"| {r.task.id} | {r.status_emoji} {r.status_label} | {r.task.difficulty} "
            f"| {r.task.category} | {tools} | {r.tool_hit_rate*100:.0f}% "
            f"| {r.latency_ms:,.0f} | {r.error or ''} |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"\n[dim]📄 Markdown report saved → {path}[/dim]")


# ── Full render ───────────────────────────────────────────────────────────────

def render_report(report: HarnessReport, output_dir: Path | None = None) -> None:
    """Print all sections and optionally save JSON + Markdown reports."""
    print_summary(report)
    print_category_breakdown(report)
    print_difficulty_breakdown(report)
    print_results_table(report)
    print_failures(report)

    if output_dir:
        ts = report.started_at.strftime("%Y%m%d_%H%M%S")
        report.save_json(output_dir / f"harness_{ts}.json")
        save_markdown_report(report, output_dir / f"harness_{ts}.md")
