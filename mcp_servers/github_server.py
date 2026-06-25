"""GitHub MCP Server — repos, issues, PRs, commits, code search.

Tools:
- get_repo_info(owner, repo)
- list_issues(owner, repo, state, labels, limit)
- get_issue(owner, repo, number)
- list_pull_requests(owner, repo, state, limit)
- get_pull_request(owner, repo, number)
- search_code(query, owner, repo)
- list_commits(owner, repo, branch, limit)
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from fastmcp import FastMCP

from config.settings import get_settings

settings = get_settings()
BASE_URL = "https://api.github.com"

mcp = FastMCP(
    name="github",
    instructions="Interact with GitHub: repos, issues, PRs, commits, and code search.",
)


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.gh_pat:
        h["Authorization"] = f"Bearer {settings.gh_pat}"
    return h


def _get(path: str, params: dict | None = None):
    resp = httpx.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _resolve(owner: str, repo: str) -> tuple[str, str]:
    owner = owner or settings.gh_default_owner
    if not owner:
        raise ValueError("owner is required (or set gh_default_owner in .env)")
    return owner, repo


@mcp.tool()
def get_repo_info(owner: str, repo: str) -> str:
    """Get metadata and stats for a GitHub repository.

    Args:
        owner: GitHub username or organization
        repo: Repository name
    """
    o, r = _resolve(owner, repo)
    d = _get(f"/repos/{o}/{r}")
    return (
        f"Repo:         {d['full_name']}\n"
        f"Description:  {d.get('description', 'N/A')}\n"
        f"Stars:        {d['stargazers_count']:,}   "
        f"Forks: {d['forks_count']:,}   "
        f"Open Issues: {d['open_issues_count']:,}\n"
        f"Language:     {d.get('language', 'N/A')}\n"
        f"Default branch: {d.get('default_branch', 'main')}\n"
        f"Last push:    {d.get('pushed_at', 'N/A')}\n"
        f"URL:          {d['html_url']}"
    )


@mcp.tool()
def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str = "",
    limit: int = 20,
) -> str:
    """List issues in a repository.

    Args:
        owner: GitHub username or org
        repo: Repository name
        state: 'open', 'closed', or 'all'
        labels: Comma-separated labels to filter by (e.g. 'bug,critical')
        limit: Max results (default 20)
    """
    o, r = _resolve(owner, repo)
    params: dict = {"state": state, "per_page": min(limit, 100), "sort": "updated"}
    if labels:
        params["labels"] = labels
    issues = _get(f"/repos/{o}/{r}/issues", params)
    lines = [f"Issues in {o}/{r} [{state}]:", ""]
    for i in issues[:limit]:
        lbls = ", ".join(lb["name"] for lb in i.get("labels", []))
        lines.append(
            f"  #{i['number']}  {i['title']}\n"
            f"    Labels: {lbls or 'none'}  |  Updated: {i['updated_at'][:10]}\n"
            f"    {i['html_url']}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_issue(owner: str, repo: str, number: int) -> str:
    """Get full details + comments of an issue.

    Args:
        owner: GitHub username or org
        repo: Repository name
        number: Issue number
    """
    o, r = _resolve(owner, repo)
    issue = _get(f"/repos/{o}/{r}/issues/{number}")
    comments = _get(f"/repos/{o}/{r}/issues/{number}/comments")
    lines = [
        f"Issue #{issue['number']}: {issue['title']}",
        f"State: {issue['state']}  |  Created: {issue['created_at'][:10]}  |  Updated: {issue['updated_at'][:10]}",
        f"Labels: {', '.join(lb['name'] for lb in issue.get('labels', []))}",
        f"URL: {issue['html_url']}",
        "",
        "── Body ──────────────────────────────────────────────────────────",
        issue.get("body") or "(no body)",
        "",
        f"── Comments ({len(comments)}) ────────────────────────────────────────",
    ]
    for c in comments[:10]:
        lines += [f"\n@{c['user']['login']} on {c['created_at'][:10]}:", c.get("body", "")]
    return "\n".join(lines)


@mcp.tool()
def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 15,
) -> str:
    """List pull requests for a repository.

    Args:
        owner: GitHub username or org
        repo: Repository name
        state: 'open', 'closed', or 'all'
        limit: Max results
    """
    o, r = _resolve(owner, repo)
    prs = _get(f"/repos/{o}/{r}/pulls", {"state": state, "per_page": min(limit, 100), "sort": "updated"})
    lines = [f"Pull Requests in {o}/{r} [{state}]:", ""]
    for pr in prs[:limit]:
        lines.append(
            f"  PR #{pr['number']}  {pr['title']}\n"
            f"    {pr['head']['ref']} → {pr['base']['ref']}  |  Updated: {pr['updated_at'][:10]}\n"
            f"    {pr['html_url']}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_pull_request(owner: str, repo: str, number: int) -> str:
    """Get full details of a pull request including changed files.

    Args:
        owner: GitHub username or org
        repo: Repository name
        number: PR number
    """
    o, r = _resolve(owner, repo)
    pr = _get(f"/repos/{o}/{r}/pulls/{number}")
    files = _get(f"/repos/{o}/{r}/pulls/{number}/files")
    file_lines = "\n".join(
        f"  {f['status']:8} {f['filename']}  (+{f['additions']} / -{f['deletions']})"
        for f in (files[:20] if isinstance(files, list) else [])
    )
    return (
        f"PR #{pr['number']}: {pr['title']}\n"
        f"State: {pr['state']}  |  Merged: {pr.get('merged', False)}\n"
        f"Branch: {pr['head']['ref']} → {pr['base']['ref']}\n"
        f"URL: {pr['html_url']}\n\n"
        f"── Description ───────────────────────────────────────────────────\n"
        f"{pr.get('body') or '(no description)'}\n\n"
        f"── Files Changed ({pr['changed_files']}) ──────────────────────────────────\n"
        f"{file_lines}"
    )


@mcp.tool()
def search_code(query: str, owner: str = "", repo: str = "") -> str:
    """Search code on GitHub.

    Args:
        query: Search terms e.g. 'auth token language:python'
        owner: Limit to this user/org (optional)
        repo: Limit to this repo — requires owner (optional)
    """
    q = query
    if owner and repo:
        q += f" repo:{owner}/{repo}"
    elif owner:
        q += f" user:{owner}"
    results = _get("/search/code", {"q": q, "per_page": 15})
    items = results.get("items", [])
    lines = [f"Code search: '{query}'  —  {results.get('total_count', 0):,} total results", ""]
    for item in items:
        lines.append(f"  📄 {item['repository']['full_name']}/{item['path']}\n     {item['html_url']}")
    return "\n".join(lines)


@mcp.tool()
def list_commits(owner: str, repo: str, branch: str = "", limit: int = 10) -> str:
    """List recent commits on a branch.

    Args:
        owner: GitHub username or org
        repo: Repository name
        branch: Branch name (default: repo default)
        limit: Number of commits
    """
    o, r = _resolve(owner, repo)
    params: dict = {"per_page": min(limit, 100)}
    if branch:
        params["sha"] = branch
    commits = _get(f"/repos/{o}/{r}/commits", params)
    lines = [f"Commits on {o}/{r} ({branch or 'default'}):", ""]
    for c in commits[:limit]:
        cm = c["commit"]
        sha = c["sha"][:7]
        date = cm["author"]["date"][:10]
        author = cm["author"]["name"]
        msg = cm["message"].split("\n")[0]
        lines.append(f"  {sha}  [{date}]  {author}: {msg}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
