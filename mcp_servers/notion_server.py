"""Notion MCP Server — search and read Notion pages and databases.

Tools:
- search_notion(query, limit)
- get_page(page_id)
- get_note_by_title(title)
- list_database_entries(database_id, status_filter, limit)
- list_recent_pages(limit)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from notion_client import Client
from fastmcp import FastMCP
from config.settings import get_settings

settings = get_settings()

mcp = FastMCP(
    name="notion",
    instructions="Read pages and search content in your Notion workspace.",
)


def _client() -> Client:
    if not settings.notion_api_key:
        raise EnvironmentError("NOTION_API_KEY is not set in .env")
    return Client(auth=settings.notion_api_key)


def _title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(r.get("plain_text", "") for r in prop.get("title", []))
    return "Untitled"


def _block_text(block: dict) -> str:
    btype = block.get("type", "")
    content = block.get(btype, {})
    rich = content.get("rich_text", [])
    text = "".join(rt.get("plain_text", "") for rt in rich)
    prefixes = {
        "heading_1": "# ", "heading_2": "## ", "heading_3": "### ",
        "bulleted_list_item": "• ", "numbered_list_item": "1. ",
        "to_do": f"{'[x]' if content.get('checked') else '[ ]'} ",
    }
    return f"{prefixes.get(btype, '')}{text}" if text else ""


def _fetch_content(notion: Client, page_id: str) -> str:
    blocks = notion.blocks.children.list(block_id=page_id, page_size=100)
    lines = []
    for b in blocks.get("results", []):
        line = _block_text(b)
        if line:
            lines.append(line)
        if b.get("has_children"):
            for cb in notion.blocks.children.list(block_id=b["id"], page_size=50).get("results", []):
                cl = _block_text(cb)
                if cl:
                    lines.append("  " + cl)
    return "\n".join(lines) or "(page has no readable content)"


@mcp.tool()
def search_notion(query: str, limit: int = 10) -> str:
    """Search for pages in Notion matching a query.

    Args:
        query: Search text
        limit: Max results
    """
    notion = _client()
    results = notion.search(query=query, page_size=min(limit, 25)).get("results", [])
    if not results:
        return f"No results for: '{query}'"
    lines = [f"Notion search '{query}' — {len(results)} results:", ""]
    for p in results[:limit]:
        lines.append(
            f"  📄 {_title(p)}\n"
            f"     ID: {p['id']}  |  Edited: {p.get('last_edited_time','')[:10]}\n"
            f"     {p.get('url','')}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_page(page_id: str) -> str:
    """Retrieve and return the full content of a Notion page.

    Args:
        page_id: Notion page ID
    """
    notion = _client()
    page = notion.pages.retrieve(page_id=page_id)
    title = _title(page)
    content = _fetch_content(notion, page_id)
    return (
        f"# {title}\n"
        f"Last edited: {page.get('last_edited_time','')[:10]}\n"
        f"URL: {page.get('url','')}\n"
        f"\n{'─'*60}\n\n{content}"
    )


@mcp.tool()
def get_note_by_title(title: str) -> str:
    """Find a Notion page by title and return its content.

    Args:
        title: Page title to search for (partial match)
    """
    notion = _client()
    results = notion.search(
        query=title, filter={"property": "object", "value": "page"}
    ).get("results", [])
    if not results:
        return f"No page found matching: '{title}'"
    return get_page(results[0]["id"])


@mcp.tool()
def list_database_entries(
    database_id: str = "",
    status_filter: str = "",
    limit: int = 20,
) -> str:
    """List entries in a Notion database.

    Args:
        database_id: Notion DB ID (defaults to NOTION_NOTES_DATABASE_ID in .env)
        status_filter: Filter by Status property value e.g. 'Done'
        limit: Max entries
    """
    notion = _client()
    db_id = database_id or settings.notion_notes_database_id
    if not db_id:
        return "No database_id provided and NOTION_NOTES_DATABASE_ID is not set."
    params: dict[str, Any] = {"database_id": db_id, "page_size": min(limit, 100)}
    if status_filter:
        params["filter"] = {"property": "Status", "status": {"equals": status_filter}}
    pages = notion.databases.query(**params).get("results", [])
    if not pages:
        return f"No entries found in database {db_id}"
    lines = [f"Database entries ({len(pages)}):", ""]
    for p in pages[:limit]:
        lines.append(f"  • {_title(p)}  [{p.get('last_edited_time','')[:10]}]  ID: {p['id']}")
    return "\n".join(lines)


@mcp.tool()
def list_recent_pages(limit: int = 10) -> str:
    """List the most recently edited pages in the Notion workspace.

    Args:
        limit: Number of pages
    """
    notion = _client()
    results = notion.search(
        query="",
        sort={"direction": "descending", "timestamp": "last_edited_time"},
        page_size=min(limit, 25),
    ).get("results", [])
    lines = [f"Recent Notion pages ({len(results)}):", ""]
    for p in results:
        lines.append(f"  📄 {_title(p)}  [{p.get('last_edited_time','')[:10]}]  {p.get('url','')}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
