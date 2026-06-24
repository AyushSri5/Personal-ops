"""
Personal Ops Agent — CLI entry point

Usage:
    python main.py                          # Interactive REPL
    python main.py --once "find latest bug" # Single query, then exit
    python main.py --no-stream              # Full response at once
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule

from agent.graph import run_once, stream_once

console = Console()

BANNER = """\
[bold cyan]╔══════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]  [bold white]⚡ Personal Ops Agent[/bold white]  [dim]LangGraph + MCP[/dim]            [bold cyan]║[/bold cyan]
[bold cyan]╠══════════════════════════════════════════════════════╣[/bold cyan]
[bold cyan]║[/bold cyan]  [dim]📁[/dim] Filesystem  [dim]🐙[/dim] GitHub  [dim]🗄️[/dim] Postgres  [dim]📝[/dim] Notion [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]  Type [bold yellow]/help[/bold yellow] for examples  ·  [bold red]Ctrl+C[/bold red] to exit          [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════╝[/bold cyan]
"""

HELP_TEXT = """
## 💡 Example prompts

**📁 Local Files**
- `list files in D:/personal_ops`
- `read the file D:/personal_ops/README.md`
- `search for all .py files`

**🐙 GitHub**
- `find the latest open bug in github repo torvalds/linux`
- `list open pull requests for owner/my-app`
- `summarize the repo owner/my-project`

**🗄️ PostgreSQL**
- `list all tables in the database`
- `show me the top 5 critical bugs`
- `how many tasks are in progress?`

**📝 Notion**
- `search notion for meeting notes`
- `draft a status update from my latest meeting note`
- `list my recent notion pages`

**Commands:** `/help`, `/clear` (reset history), `/exit`
"""


async def repl(stream: bool = True) -> None:
    """Interactive REPL loop."""
    console.print(BANNER)
    history: list[tuple[str, str]] = []

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye! 👋[/dim]")
            break

        if not user_input:
            continue

        match user_input.lower():
            case "/exit" | "/quit" | "exit" | "quit":
                console.print("[dim]Goodbye! 👋[/dim]")
                break
            case "/help" | "help":
                console.print(Markdown(HELP_TEXT))
                continue
            case "/clear":
                history.clear()
                console.print("[dim]✓ History cleared[/dim]")
                continue
            case "/history":
                for i, (role, msg) in enumerate(history, 1):
                    console.print(f"[dim]{i}. [{role}] {msg[:80]}[/dim]")
                continue

        console.print()
        console.print(Rule("[bold magenta]Agent[/bold magenta]", style="magenta"))

        try:
            if stream:
                parts: list[str] = []
                async for chunk in stream_once(user_input, list(history)):
                    console.print(chunk, end="", highlight=False)
                    parts.append(chunk)
                response = "".join(parts)
                console.print()
            else:
                with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
                    response = await run_once(user_input, list(history))
                console.print(Markdown(response))

        except Exception as exc:
            console.print(f"\n[bold red]Error:[/bold red] {exc}")
            console.print_exception(show_locals=False)
            continue

        history.append(("user", user_input))
        history.append(("assistant", response))
        history = history[-20:]  # keep last 10 exchanges


async def once(message: str, stream: bool = True) -> None:
    """Run a single query and exit."""
    console.print(Panel(f"[bold white]{message}[/bold white]", title="[cyan]Query[/cyan]", border_style="cyan"))
    console.print()
    try:
        if stream:
            async for chunk in stream_once(message):
                console.print(chunk, end="", highlight=False)
            console.print()
        else:
            with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
                response = await run_once(message)
            console.print(Markdown(response))
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        console.print_exception()
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Ops Agent")
    parser.add_argument("--once", "-o", metavar="QUERY", help="Run a single query and exit")
    parser.add_argument("--no-stream", action="store_true", help="Show full response at once")
    args = parser.parse_args()
    stream = not args.no_stream

    if args.once:
        asyncio.run(once(args.once, stream=stream))
    else:
        asyncio.run(repl(stream=stream))


if __name__ == "__main__":
    main()
