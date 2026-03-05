"""Jira REST API helpers."""

import json
import base64
import urllib.request
import urllib.parse

from config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN


def _jira_get(path: str) -> dict:
    if not JIRA_API_TOKEN:
        return {}
    creds = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    url = f"{JIRA_BASE_URL}/rest/api/3/{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_my_issues() -> list[dict]:
    """Get issues assigned to the current user that are not done."""
    if not JIRA_API_TOKEN:
        return []
    jql = urllib.parse.quote(
        "assignee = currentUser() AND status NOT IN (Done, Closed, Resolved) ORDER BY updated DESC"
    )
    data = _jira_get(f"search/jql?jql={jql}&maxResults=20&fields=summary,status,priority,updated")
    issues = data.get("issues", [])
    return [
        {
            "key": i["key"],
            "summary": i["fields"]["summary"],
            "status": i["fields"]["status"]["name"],
            "priority": i["fields"].get("priority", {}).get("name", "?"),
        }
        for i in issues
    ]


def get_blocked_issues() -> list[dict]:
    """Get issues that are blocked or flagged."""
    if not JIRA_API_TOKEN:
        return []
    jql = urllib.parse.quote(
        'assignee = currentUser() AND (status = Blocked OR "Flagged" IS NOT EMPTY) ORDER BY updated DESC'
    )
    try:
        data = _jira_get(f"search/jql?jql={jql}&maxResults=10&fields=summary,status,priority")
        return [
            {
                "key": i["key"],
                "summary": i["fields"]["summary"],
                "status": i["fields"]["status"]["name"],
            }
            for i in data.get("issues", [])
        ]
    except Exception:
        return []


def format_issue(issue: dict) -> str:
    status_icons = {
        "In Progress": "🔵",
        "Selected for Development": "⚪",
        "To Do": "⚪",
        "Blocked": "🔴",
        "In Review": "🟡",
        "Code Review": "🟡",
        "QA": "🟢",
    }
    icon = status_icons.get(issue["status"], "⚪")
    return f"  {icon} [{issue['key']}] {issue['summary']} ({issue['status']})"


# --- Board overviews ---
# Add your own board IDs here. Find board IDs via:
# GET https://your-org.atlassian.net/rest/agile/1.0/board

BOARDS: dict[str, dict] = {
    # "MY_BOARD": {"id": 123, "name": "My Team Board", "quick_filter_jql": "status not in (Done, Cancelled)"},
}


def _agile_get(path: str) -> dict:
    if not JIRA_API_TOKEN:
        return {}
    creds = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    url = f"{JIRA_BASE_URL}/rest/agile/1.0/{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_board_overview(board_key: str) -> dict:
    """Get a summary of a Jira board: counts per status + active items."""
    board = BOARDS.get(board_key)
    if not board or not JIRA_API_TOKEN:
        return {}

    jql = board.get("quick_filter_jql") or ""
    jql_param = f"&jql={urllib.parse.quote(jql)}" if jql else ""
    fields = "summary,status,assignee,priority,issuetype,updated"

    try:
        data = _agile_get(f"board/{board['id']}/issue?maxResults=100&fields={fields}{jql_param}")
    except Exception:
        return {"name": board["name"], "error": True}

    issues = data.get("issues", [])
    total = data.get("total", len(issues))

    from collections import Counter
    status_counts = Counter()
    active_items = []
    active_statuses = {"In Progress", "Code Review", "Design Review", "QA", "In Review"}

    for i in issues:
        status = i["fields"]["status"]["name"]
        status_counts[status] += 1
        if status in active_statuses:
            assignee = i["fields"].get("assignee")
            name = assignee.get("displayName", "?").split()[0] if assignee else "Unassigned"
            active_items.append({
                "key": i["key"],
                "summary": i["fields"]["summary"][:65],
                "status": status,
                "assignee": name,
            })

    return {
        "name": board["name"],
        "total": total,
        "status_counts": dict(status_counts),
        "active_items": active_items,
    }


def format_board_overview(overview: dict) -> list[str]:
    """Format a board overview into lines for the briefing."""
    lines = []
    if overview.get("error"):
        lines.append(f"  ⚠️ {overview['name']}: error fetching data")
        return lines

    lines.append(f"  **{overview['name']}** — {overview['total']} tickets")

    counts = overview.get("status_counts", {})
    active_statuses = ["In Progress", "Code Review", "Design Review", "QA", "In Review"]
    waiting_statuses = ["Ready", "To Refine", "Selected for Development", "To Do"]

    active_count = sum(counts.get(s, 0) for s in active_statuses)
    waiting_count = sum(counts.get(s, 0) for s in waiting_statuses)
    backlog_count = counts.get("Backlog", 0)

    parts = []
    if active_count:
        parts.append(f"🔵 {active_count} active")
    if waiting_count:
        parts.append(f"⚪ {waiting_count} waiting")
    if backlog_count:
        parts.append(f"📋 {backlog_count} backlog")
    if parts:
        lines.append(f"  {' | '.join(parts)}")

    for item in overview.get("active_items", [])[:8]:
        icon = {"In Progress": "🔵", "Code Review": "🟡", "Design Review": "🟠", "QA": "🟢", "In Review": "🟡"}.get(item["status"], "⚪")
        lines.append(f"    {icon} [{item['key']}] {item['summary']} — {item['assignee']} ({item['status']})")

    return lines
