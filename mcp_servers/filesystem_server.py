"""Filesystem MCP Server — safe local file access.

Tools:
- read_file(path)
- write_file(path, content)
- list_directory(path)
- search_files(pattern, root)
- file_info(path)
"""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

# Add project root to sys.path so `config` is importable
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from config.settings import get_settings

settings = get_settings()
ROOT = settings.local_files_root

mcp = FastMCP(
    name="filesystem",
    instructions=f"Safe read/write access to local files under: {ROOT}",
)


def _safe(path: str) -> Path:
    resolved = (ROOT / path).resolve()
    if not str(resolved).startswith(str(ROOT.resolve())):
        raise PermissionError(f"Access denied: '{path}' is outside the allowed root '{ROOT}'")
    return resolved


@mcp.tool()
def read_file(path: str) -> str:
    """Read the full text content of a file.

    Args:
        path: Path to the file (relative to LOCAL_FILES_ROOT or absolute)
    """
    p = _safe(path)
    if not p.exists():
        raise FileNotFoundError(f"Not found: {path}")
    return p.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file (creates parent directories if needed).

    Args:
        path: Destination path
        content: Text to write
    """
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written {len(content)} chars to {p}"


@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List files and folders inside a directory.

    Args:
        path: Directory path (default: LOCAL_FILES_ROOT)
    """
    p = _safe(path)
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
    lines = [f"Contents of {p}:", ""]
    for e in entries:
        if e.is_dir():
            lines.append(f"  📁 {e.name}/")
        else:
            lines.append(f"  📄 {e.name}  ({e.stat().st_size:,} bytes)")
    return "\n".join(lines)


@mcp.tool()
def search_files(pattern: str, root: str = ".") -> str:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob e.g. '*.py', '**/*.md'
        root: Directory to search (relative to LOCAL_FILES_ROOT)
    """
    p = _safe(root)
    matches = [
        str(f.relative_to(ROOT))
        for f in p.rglob("*")
        if fnmatch.fnmatch(f.name, pattern.split("/")[-1])
    ]
    return "\n".join(matches[:200]) if matches else f"No matches for '{pattern}'"


@mcp.tool()
def file_info(path: str) -> str:
    """Return metadata (size, dates) for a file or directory.

    Args:
        path: Target path
    """
    import datetime
    p = _safe(path)
    if not p.exists():
        raise FileNotFoundError(f"Not found: {path}")
    s = p.stat()
    return (
        f"Path:     {p}\n"
        f"Type:     {'directory' if p.is_dir() else 'file'}\n"
        f"Size:     {s.st_size:,} bytes\n"
        f"Modified: {datetime.datetime.fromtimestamp(s.st_mtime)}\n"
        f"Created:  {datetime.datetime.fromtimestamp(s.st_ctime)}"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
