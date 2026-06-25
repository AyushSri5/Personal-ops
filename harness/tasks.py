"""
Harness task definitions — 40 tasks across 6 categories.

Each Task defines:
  - id            : unique slug
  - category      : tool group being tested
  - difficulty    : easy / medium / hard
  - prompt        : exact user prompt sent to the agent
  - expected_tools: tools the agent SHOULD call (used for scoring)
  - description   : what capability this validates
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    id: str
    category: str
    difficulty: str          # easy | medium | hard
    prompt: str
    expected_tools: list[str]
    description: str


# ─────────────────────────────────────────────────────────────────────────────
# 📁  FILESYSTEM  (tasks 01–08)
# ─────────────────────────────────────────────────────────────────────────────
FILESYSTEM_TASKS: list[Task] = [
    Task(
        id="fs-01",
        category="filesystem",
        difficulty="easy",
        prompt="List all files in D:/personal_ops",
        expected_tools=["list_directory"],
        description="Basic directory listing",
    ),
    Task(
        id="fs-02",
        category="filesystem",
        difficulty="easy",
        prompt="Read the file D:/personal_ops/README.md",
        expected_tools=["read_file"],
        description="Read a specific file",
    ),
    Task(
        id="fs-03",
        category="filesystem",
        difficulty="easy",
        prompt="Find all Python files in D:/personal_ops",
        expected_tools=["search_files"],
        description="Glob search for .py files",
    ),
    Task(
        id="fs-04",
        category="filesystem",
        difficulty="medium",
        prompt="Show me metadata (size, modified date) of D:/personal_ops/main.py",
        expected_tools=["file_info"],
        description="File metadata retrieval",
    ),
    Task(
        id="fs-05",
        category="filesystem",
        difficulty="medium",
        prompt="List all files inside the mcp_servers folder in D:/personal_ops",
        expected_tools=["list_directory"],
        description="Sub-directory listing",
    ),
    Task(
        id="fs-06",
        category="filesystem",
        difficulty="medium",
        prompt="Read D:/personal_ops/requirements.txt and list all packages",
        expected_tools=["read_file"],
        description="Parse requirements file",
    ),
    Task(
        id="fs-07",
        category="filesystem",
        difficulty="hard",
        prompt="Summarize the entire D:/personal_ops project: its purpose, structure, and key components",
        expected_tools=["list_directory", "read_file"],
        description="Multi-file repo summarization",
    ),
    Task(
        id="fs-08",
        category="filesystem",
        difficulty="hard",
        prompt=(
            "Write a file D:/personal_ops/NOTES.md with a brief description "
            "of what this project does, then confirm what was written"
        ),
        expected_tools=["write_file"],
        description="Write a new file",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 🐙  GITHUB  (tasks 09–18)
# ─────────────────────────────────────────────────────────────────────────────
GITHUB_TASKS: list[Task] = [
    Task(
        id="gh-01",
        category="github",
        difficulty="easy",
        prompt="Get info about the GitHub repo microsoft/vscode",
        expected_tools=["get_repo_info"],
        description="Fetch repo metadata",
    ),
    Task(
        id="gh-02",
        category="github",
        difficulty="easy",
        prompt="List the 10 most recently updated open issues in microsoft/vscode",
        expected_tools=["list_issues"],
        description="List open issues",
    ),
    Task(
        id="gh-03",
        category="github",
        difficulty="easy",
        prompt="List open pull requests for facebook/react",
        expected_tools=["list_pull_requests"],
        description="List open PRs",
    ),
    Task(
        id="gh-04",
        category="github",
        difficulty="easy",
        prompt="Show the last 10 commits on the main branch of torvalds/linux",
        expected_tools=["list_commits"],
        description="Recent commit history",
    ),
    Task(
        id="gh-05",
        category="github",
        difficulty="medium",
        prompt="Find the latest open bug in microsoft/vscode (filter by bug label)",
        expected_tools=["list_issues"],
        description="Filtered issue search for bugs",
    ),
    Task(
        id="gh-06",
        category="github",
        difficulty="medium",
        prompt="Get full details of issue #1 in microsoft/vscode including its comments",
        expected_tools=["get_issue"],
        description="Single issue deep-dive",
    ),
    Task(
        id="gh-07",
        category="github",
        difficulty="medium",
        prompt="Search for code containing 'useState' in facebook/react",
        expected_tools=["search_code"],
        description="Code search within a repo",
    ),
    Task(
        id="gh-08",
        category="github",
        difficulty="medium",
        prompt="How many open issues does the python/cpython repo have?",
        expected_tools=["get_repo_info"],
        description="Extract specific stat from repo info",
    ),
    Task(
        id="gh-09",
        category="github",
        difficulty="hard",
        prompt=(
            "Compare microsoft/vscode and facebook/react: "
            "which has more stars, more open issues, and more recent activity?"
        ),
        expected_tools=["get_repo_info"],
        description="Multi-repo comparison",
    ),
    Task(
        id="gh-10",
        category="github",
        difficulty="hard",
        prompt=(
            "Summarize the top 5 open bugs in microsoft/vscode: "
            "list titles, labels, and last updated dates"
        ),
        expected_tools=["list_issues"],
        description="Bug summary report",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 🗄️  POSTGRES — READ  (tasks 19–25)
# ─────────────────────────────────────────────────────────────────────────────
POSTGRES_READ_TASKS: list[Task] = [
    Task(
        id="pg-r-01",
        category="postgres_read",
        difficulty="easy",
        prompt="List all tables in the database",
        expected_tools=["list_tables"],
        description="Database table discovery",
    ),
    Task(
        id="pg-r-02",
        category="postgres_read",
        difficulty="easy",
        prompt="Show me the structure of the bugs table",
        expected_tools=["describe_table"],
        description="Table schema inspection",
    ),
    Task(
        id="pg-r-03",
        category="postgres_read",
        difficulty="easy",
        prompt="Show me a sample of 5 rows from the tasks table",
        expected_tools=["get_table_sample"],
        description="Table row preview",
    ),
    Task(
        id="pg-r-04",
        category="postgres_read",
        difficulty="medium",
        prompt="How many open bugs are there in the database?",
        expected_tools=["run_query"],
        description="Aggregate COUNT query",
    ),
    Task(
        id="pg-r-05",
        category="postgres_read",
        difficulty="medium",
        prompt="Show all critical or high severity bugs that are still open",
        expected_tools=["run_query"],
        description="Filtered query with WHERE clause",
    ),
    Task(
        id="pg-r-06",
        category="postgres_read",
        difficulty="medium",
        prompt="What is the database size and version?",
        expected_tools=["get_db_stats"],
        description="Database stats retrieval",
    ),
    Task(
        id="pg-r-07",
        category="postgres_read",
        difficulty="hard",
        prompt="Give me a bug report summary: count bugs by severity and status",
        expected_tools=["run_query"],
        description="GROUP BY aggregation query",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 🗄️  POSTGRES — WRITE  (tasks 26–31)
# ─────────────────────────────────────────────────────────────────────────────
POSTGRES_WRITE_TASKS: list[Task] = [
    Task(
        id="pg-w-01",
        category="postgres_write",
        difficulty="easy",
        prompt=(
            "Log a new bug: title='Login page crash on Safari', "
            "severity='high', repo='my-app'"
        ),
        expected_tools=["create_bug"],
        description="Insert a new bug record",
    ),
    Task(
        id="pg-w-02",
        category="postgres_write",
        difficulty="easy",
        prompt=(
            "Create a new task: title='Review pull requests', "
            "assignee='alice', due_date='2025-07-10'"
        ),
        expected_tools=["create_task"],
        description="Insert a new task record",
    ),
    Task(
        id="pg-w-03",
        category="postgres_write",
        difficulty="medium",
        prompt=(
            "Store a meeting note: title='Sprint Planning - Week 26', "
            "date='2025-06-24', attendees='Alice, Bob, Carol', "
            "body='Discussed Q3 roadmap. Agreed to prioritise auth overhaul. "
            "Alice owns backend, Bob owns frontend. Next meeting in 2 weeks.'"
        ),
        expected_tools=["create_meeting_note"],
        description="Insert a meeting note with attendees",
    ),
    Task(
        id="pg-w-04",
        category="postgres_write",
        difficulty="medium",
        prompt="Mark task with ID 1 as done",
        expected_tools=["update_task_status"],
        description="Update task status",
    ),
    Task(
        id="pg-w-05",
        category="postgres_write",
        difficulty="medium",
        prompt="Mark bug with ID 1 as resolved",
        expected_tools=["update_bug_status"],
        description="Update bug status",
    ),
    Task(
        id="pg-w-06",
        category="postgres_write",
        difficulty="hard",
        prompt=(
            "Create an AI meeting note for today's standup: "
            "title='Daily Standup 2025-06-24', attendees='Dev Team', "
            "body='Completed: API integration. In progress: UI redesign. "
            "Blockers: Waiting for design assets. Action: Bob to follow up with design team.'"
            " Then store it in the database."
        ),
        expected_tools=["create_meeting_note"],
        description="Draft and store a structured meeting note",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 📝  NOTION  (tasks 32–37)
# ─────────────────────────────────────────────────────────────────────────────
NOTION_TASKS: list[Task] = [
    Task(
        id="nt-01",
        category="notion",
        difficulty="easy",
        prompt="List my most recently edited Notion pages",
        expected_tools=["list_recent_pages"],
        description="Recent pages listing",
    ),
    Task(
        id="nt-02",
        category="notion",
        difficulty="easy",
        prompt="Search Notion for 'meeting notes'",
        expected_tools=["search_notion"],
        description="Full-text Notion search",
    ),
    Task(
        id="nt-03",
        category="notion",
        difficulty="medium",
        prompt="Find and read the most recent meeting note in Notion",
        expected_tools=["search_notion", "get_page"],
        description="Search then read a page",
    ),
    Task(
        id="nt-04",
        category="notion",
        difficulty="medium",
        prompt="Search Notion for 'sprint review' and summarize any decisions made",
        expected_tools=["search_notion", "get_page"],
        description="Search + summarize content",
    ),
    Task(
        id="nt-05",
        category="notion",
        difficulty="hard",
        prompt=(
            "Find my latest meeting note in Notion and draft a professional "
            "Slack status update highlighting key decisions and action items"
        ),
        expected_tools=["search_notion", "get_page"],
        description="Meeting note → status update generation",
    ),
    Task(
        id="nt-06",
        category="notion",
        difficulty="hard",
        prompt="List entries from my Notion notes database",
        expected_tools=["list_database_entries"],
        description="Database entry listing",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 🔀  CROSS-TOOL  (tasks 38–45)
# ─────────────────────────────────────────────────────────────────────────────
CROSS_TOOL_TASKS: list[Task] = [
    Task(
        id="cx-01",
        category="cross_tool",
        difficulty="medium",
        prompt=(
            "Check GitHub for open bugs in microsoft/vscode AND "
            "check the local postgres bugs table — give me a combined bug summary"
        ),
        expected_tools=["list_issues", "run_query"],
        description="GitHub + Postgres cross-tool bug aggregation",
    ),
    Task(
        id="cx-02",
        category="cross_tool",
        difficulty="medium",
        prompt=(
            "Read the README.md file from D:/personal_ops and "
            "compare it with the repo info from GitHub for microsoft/vscode"
        ),
        expected_tools=["read_file", "get_repo_info"],
        description="Filesystem + GitHub comparison",
    ),
    Task(
        id="cx-03",
        category="cross_tool",
        difficulty="hard",
        prompt=(
            "Search Notion for a meeting note, extract any action items, "
            "and create tasks in the Postgres database for each one"
        ),
        expected_tools=["search_notion", "get_page", "create_task"],
        description="Notion → Postgres action item extraction",
    ),
    Task(
        id="cx-04",
        category="cross_tool",
        difficulty="hard",
        prompt=(
            "Summarize the D:/personal_ops project structure from local files, "
            "then log a bug in Postgres: title='Add unit tests', severity='medium'"
        ),
        expected_tools=["list_directory", "create_bug"],
        description="Filesystem read + Postgres write",
    ),
    Task(
        id="cx-05",
        category="cross_tool",
        difficulty="hard",
        prompt=(
            "Find the latest open issues in microsoft/vscode on GitHub, "
            "pick the most critical one, and store it as a bug in Postgres"
        ),
        expected_tools=["list_issues", "create_bug"],
        description="GitHub issue → Postgres bug ingestion",
    ),
    Task(
        id="cx-06",
        category="cross_tool",
        difficulty="hard",
        prompt=(
            "Read the meeting notes from Notion, draft a status update, "
            "and save it as a file at D:/personal_ops/status_update.md"
        ),
        expected_tools=["search_notion", "get_page", "write_file"],
        description="Notion read → filesystem write",
    ),
    Task(
        id="cx-07",
        category="cross_tool",
        difficulty="hard",
        prompt=(
            "Show me a full ops dashboard: "
            "1) count open bugs from Postgres "
            "2) list 3 recent GitHub issues from microsoft/vscode "
            "3) list recent Notion pages"
        ),
        expected_tools=["run_query", "list_issues", "list_recent_pages"],
        description="Three-tool ops dashboard",
    ),
    Task(
        id="cx-08",
        category="cross_tool",
        difficulty="hard",
        prompt=(
            "Analyse the D:/personal_ops project: read key Python files, "
            "identify what could be improved, and create a task in Postgres "
            "for the most important improvement"
        ),
        expected_tools=["list_directory", "read_file", "create_task"],
        description="Code review → task creation",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# Combined registry
# ─────────────────────────────────────────────────────────────────────────────
ALL_TASKS: list[Task] = (
    FILESYSTEM_TASKS
    + GITHUB_TASKS
    + POSTGRES_READ_TASKS
    + POSTGRES_WRITE_TASKS
    + NOTION_TASKS
    + CROSS_TOOL_TASKS
)

TASKS_BY_CATEGORY: dict[str, list[Task]] = {
    "filesystem":     FILESYSTEM_TASKS,
    "github":         GITHUB_TASKS,
    "postgres_read":  POSTGRES_READ_TASKS,
    "postgres_write": POSTGRES_WRITE_TASKS,
    "notion":         NOTION_TASKS,
    "cross_tool":     CROSS_TOOL_TASKS,
}

TASKS_BY_ID: dict[str, Task] = {t.id: t for t in ALL_TASKS}
