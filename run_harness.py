"""
Personal Ops Agent — Harness Entry Point

Runs 30–50 tasks against the agent and produces a detailed report.

Usage:
    # Run all 40 tasks
    python run_harness.py

    # Run a specific category only
    python run_harness.py --category filesystem
    python run_harness.py --category github
    python run_harness.py --category postgres_read
    python run_harness.py --category postgres_write
    python run_harness.py --category notion
    python run_harness.py --category cross_tool

    # Run specific task IDs
    python run_harness.py --ids fs-01 fs-02 gh-01

    # Skip categories (e.g. if Notion API key not set)
    python run_harness.py --skip notion cross_tool

    # Run only easy tasks
    python run_harness.py --difficulty easy

    # Set per-task timeout (default 120s)
    python run_harness.py --timeout 60

    # Save reports to a directory
    python run_harness.py --output-dir harness_results/

    # Run with concurrency (parallel tasks — may hit rate limits)
    python run_harness.py --concurrency 3

    # Dry-run: list tasks without running them
    python run_harness.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from harness.report import render_report
from harness.runner import DEFAULT_CONCURRENCY, DEFAULT_TIMEOUT_S, run_harness
from harness.tasks import ALL_TASKS, TASKS_BY_CATEGORY, Task

console = Console()

CATEGORY_EMOJI = {
    "filesystem":     "📁",
    "github":         "🐙",
    "postgres_read":  "🗄️ R",
    "postgres_write": "🗄️ W",
    "notion":         "📝",
    "cross_tool":     "🔀",
}


def print_task_list(tasks: list[Task]) -> None:
    """Dry-run: print task list without running."""
    console.print()
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white")
    table.add_column("ID",         style="cyan", width=10)
    table.add_column("Category",   width=14)
    table.add_column("Difficulty", width=10)
    table.add_column("Expected Tools",     width=35)
    table.add_column("Prompt",     width=55)

    diff_style = {"easy": "green", "medium": "yellow", "hard": "red"}
    for t in tasks:
        table.add_row(
            t.id,
            f"{CATEGORY_EMOJI.get(t.category, '')} {t.category}",
            f"[{diff_style.get(t.difficulty, '')}]{t.difficulty}[/]",
            ", ".join(t.expected_tools),
            t.prompt[:55] + ("…" if len(t.prompt) > 55 else ""),
        )

    console.print(table)
    console.print(f"\n[bold white]Total: {len(tasks)} tasks[/bold white]")


def select_tasks(args: argparse.Namespace) -> list[Task]:
    """Apply CLI filters to select which tasks to run."""
    tasks = list(ALL_TASKS)

    if args.category:
        tasks = [t for t in tasks if t.category == args.category]
        if not tasks:
            console.print(f"[red]No tasks found for category '{args.category}'[/red]")
            console.print(f"Valid categories: {', '.join(TASKS_BY_CATEGORY)}")
            sys.exit(1)

    if args.ids:
        id_set = set(args.ids)
        tasks = [t for t in tasks if t.id in id_set]
        missing = id_set - {t.id for t in tasks}
        if missing:
            console.print(f"[yellow]Warning: unknown task IDs: {', '.join(missing)}[/yellow]")

    if args.difficulty:
        tasks = [t for t in tasks if t.difficulty == args.difficulty]

    if args.skip:
        skip_set = set(args.skip)
        tasks = [t for t in tasks if t.category not in skip_set]

    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Personal Ops Agent — Evaluation Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--category",    metavar="CAT",  help="Run only this category")
    parser.add_argument("--ids",         nargs="+",      help="Run specific task IDs")
    parser.add_argument("--difficulty",  choices=["easy", "medium", "hard"], help="Filter by difficulty")
    parser.add_argument("--skip",        nargs="+",      metavar="CAT",  help="Skip these categories")
    parser.add_argument("--timeout",     type=int,       default=DEFAULT_TIMEOUT_S, help="Per-task timeout in seconds")
    parser.add_argument("--concurrency", type=int,       default=DEFAULT_CONCURRENCY, help="Parallel tasks")
    parser.add_argument("--output-dir",  metavar="DIR",  help="Directory to save JSON + Markdown reports")
    parser.add_argument("--dry-run",     action="store_true", help="List tasks without running them")
    args = parser.parse_args()

    tasks = select_tasks(args)

    # ── Header ─────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold white]⚡ Personal Ops Agent — Evaluation Harness[/bold white]\n\n"
        f"  Tasks selected:  [cyan]{len(tasks)}[/cyan]\n"
        f"  Timeout/task:    [cyan]{args.timeout}s[/cyan]\n"
        f"  Concurrency:     [cyan]{args.concurrency}[/cyan]\n"
        f"  Skip categories: [yellow]{', '.join(args.skip) if args.skip else 'none'}[/yellow]",
        border_style="cyan",
    ))

    if args.dry_run:
        print_task_list(tasks)
        return

    if not tasks:
        console.print("[red]No tasks selected. Exiting.[/red]")
        sys.exit(1)

    # ── Run ─────────────────────────────────────────────────────────────────
    output_dir = Path(args.output_dir) if args.output_dir else None

    report = asyncio.run(
        run_harness(
            tasks=tasks,
            concurrency=args.concurrency,
            timeout_s=args.timeout,
            skip_categories=set(args.skip) if args.skip else None,
        )
    )

    # ── Render ───────────────────────────────────────────────────────────────
    render_report(report, output_dir=output_dir)

    # Exit with non-zero code if any failures
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
