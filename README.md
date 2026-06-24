# ⚡ Personal Ops Agent

> A LangGraph-powered assistant that connects to local files, GitHub, PostgreSQL, and Notion via MCP.

## Quick Start

```powershell
# 1. Open THIS folder in VS Code (not the parent!)
# File → Open Folder → D:\personal_ops

# 2. Create venv
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
copy .env.example .env
# Edit .env — add OPENAI_API_KEY, GITHUB_PAT, NOTION_API_KEY

# 5. Start Postgres (optional, requires Docker)
docker-compose up -d

# 6. Run the agent
python main.py
```

## Example Prompts

```
summarize the repo at D:/personal_ops
find the latest open bug in github repo owner/repo
list all tables in the database
draft a status update from my latest meeting note in Notion
```

## Project Structure

```
D:\personal_ops\
├── agent/
│   ├── graph.py        # LangGraph ReAct agent
│   ├── state.py        # AgentState
│   └── prompts.py      # System prompt
├── config/
│   └── settings.py     # Pydantic-settings (.env loader)
├── mcp_servers/
│   ├── filesystem_server.py
│   ├── github_server.py
│   ├── postgres_server.py
│   └── notion_server.py
├── docker/postgres/init.sql
├── docker-compose.yml
├── main.py             # CLI entry point
├── requirements.txt
└── .env.example
```
