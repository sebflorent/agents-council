# Agents Council

A lightweight AI assistant setup for Engineering Managers, running inside [Cursor IDE](https://cursor.sh). No extra app needed — everything works inline in your editor, connected to your real tools via MCP (Model Context Protocol).

## What it does

- **Daily briefing** — pulls your calendar, unread emails, and Jira tickets every morning into a structured Markdown file
- **EM Attention OS** — turns calendar and Chief-of-Staff context into a five-area, 100-point attention budget with a daily "letter block" and private weekly review
- **Agent council** — specialist AI agents for EM tasks: 1:1 prep, PR review, career coaching
- **Live tool access** — Jira, Slack, GitHub, Google Calendar all accessible directly from chat

## EM Attention Operating System

The Attention OS is a local, dependency-free pilot for making an EM's focus
intentional across Delivery, People, Support, Technical direction, and Team
future.

```bash
python3 -m attention_os daily \
  --calendar-json examples/attention-os/calendar.example.json
```

See [the setup and five-day pilot guide](docs/em-attention-os.md). A project
skill is included at `.cursor/skills/em-attention-os/SKILL.md`, so teams that
clone the repository can use the same workflow in Cursor.

## Agents

| Agent | Trigger | Output |
|---|---|---|
| **Senior EM Agent** | 1:1 prep, feedback, performance reviews | `SUMMARY / ACTIONS / MILESTONES` |
| **PR Reviewer Agent** | PR diff or commit link | `VERDICT / TOP RISKS / ACTIONS` |
| **Career Coach Agent** | Career conversations, skill gaps | `VISION / SKILL_GAPS / 3_MONTH_PLAN` |
| **Council Convenor** | Any EM request — runs all 3 agents | Full JSON report |

## Prerequisites

- [Cursor IDE](https://cursor.sh) (any recent version)
- Python 3.11+
- A Google Cloud project with Gmail API + Calendar API enabled
- A Jira account with API token access

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-org/agents-council.git
cd agents-council
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values (see comments in the file).

### 3. Get your Google refresh token

```bash
python3 briefings/get_token.py
```

This opens a browser, asks you to log in with your work Google account, and prints a refresh token. Paste it into `.env` as `GOOGLE_REFRESH_TOKEN`.

> The script requests read-only access to Gmail and Calendar. It does not store any data.

### 4. Configure Jira boards (optional)

Open `briefings/jira_api.py` and add your board IDs to the `BOARDS` dict:

```python
BOARDS = {
    "MY_TEAM": {"id": 123, "name": "My Team Board", "quick_filter_jql": "status not in (Done, Cancelled)"},
}
```

Find your board ID via: `GET https://your-org.atlassian.net/rest/agile/1.0/board`

### 5. Run your first briefing

```bash
# Load env vars and run
export $(cat .env | xargs) && python3 briefings/briefing.py

# English output
export $(cat .env | xargs) && python3 briefings/briefing.py --lang en
```

The briefing is saved to `briefings/output/YYYY-MM-DD-pro.md`.

## MCP Connections (for live chat access)

The agents and briefing can also be triggered directly from Cursor chat, with live data from your tools. Configure these MCP servers in Cursor settings (`~/.cursor/mcp.json`):

- **[Atlassian MCP](https://github.com/sooperset/mcp-atlassian)** — Jira and Confluence
- **[Slack MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/slack)** — Slack messaging
- **[GitHub MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/github)** — PRs and code
- **Google Calendar MCP** — Calendar read/write (see `google-calendar-mcp/` folder)

Once connected, you can ask things like:

```
"Show me all of [engineer]'s open Jira tickets before our 1:1"
"Draft a Slack message to #engineering-managers about X"
"Prepare 1:1 notes for my meeting with [person] at 15:00"
"Review this PR and flag the top risks"
```

## Agent usage (via CLI)

```bash
# List available agents
python3 -m agents_council.cli --modes modes.json list

# Invoke a specific agent
python3 -m agents_council.cli invoke senior_em_agent "Prepare 1:1 notes for Alice, she's been struggling with scope creep"

# Prepare full council dispatch
python3 -m agents_council.cli council "Alice wants to move to Staff Engineer in 12 months"
```

## File structure

```
agents-council/
├── .cursorrules              # Cursor integration rules
├── .env.example              # Environment variable template
├── modes.json                # Agent definitions
├── requirements.txt
├── briefings/
│   ├── briefing.py           # Briefing generator
│   ├── config.py             # Config (reads from env)
│   ├── google_api.py         # Calendar + Gmail helpers
│   ├── jira_api.py           # Jira REST helpers
│   ├── get_token.py          # Google OAuth helper
│   └── output/               # Generated briefings (git-ignored)
└── agents_council/
    ├── agents.py             # Agent registry + executor
    ├── models.py             # Pydantic models
    └── cli.py                # CLI for testing
```

## Security notes

- Never commit `.env` — it is git-ignored by default
- The Google OAuth token is stored locally in `.env` only
- Jira API tokens are personal and scoped to your account
- The briefing output folder is also git-ignored (contains personal calendar/email data)

## License

MIT
