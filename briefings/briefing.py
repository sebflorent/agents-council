#!/usr/bin/env python3
"""
Daily professional briefing generator.
Pulls data from Google Calendar, Gmail, and Jira.

Usage:
  python3 briefing.py          # generates today's briefing
  python3 briefing.py --lang en  # English output (default: fr)
"""

import sys
import os
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))

from config import WORK_REFRESH_TOKEN, WORK_EMAIL, TIMEZONE, BRIEFING_OUTPUT_DIR
from google_api import (
    get_access_token, get_today_events, get_recent_emails, get_unread_count,
    is_ooo_all_day, is_ooo_afternoon_only, format_event, format_email,
)
from jira_api import get_my_issues, get_blocked_issues, format_issue, get_board_overview, format_board_overview


OOO_KEYWORDS = ["ooo", "out of office", "vacances", "vacation", "congé", "congés", "absent", "off"]


def is_ooo_event(ev: dict) -> bool:
    summary = (ev.get("summary") or "").lower()
    return any(kw in summary for kw in OOO_KEYWORDS)


def build_briefing(lang: str = "fr") -> str | None:
    now = datetime.now(ZoneInfo(TIMEZONE))

    if now.weekday() >= 5:
        return None

    if not WORK_REFRESH_TOKEN:
        return "⚠️ GOOGLE_REFRESH_TOKEN not set. Run: python3 briefings/get_token.py"

    token = get_access_token(WORK_REFRESH_TOKEN)
    events = get_today_events(token, WORK_EMAIL)

    if is_ooo_all_day(events) and not is_ooo_afternoon_only(events):
        return None

    EN = lang == "en"
    lines = []

    title = f"💼 Daily Work Briefing — {now.strftime('%A %B %d, %Y')}" if EN else f"💼 Briefing Pro — {now.strftime('%A %d %B %Y')}"
    lines.append(f"# {title}")
    lines.append("")

    if is_ooo_afternoon_only(events):
        msg = "> ⚠️ OoO this afternoon — morning briefing only" if EN else "> ⚠️ OoO cet après-midi — briefing matinal uniquement"
        lines.append(msg)
        lines.append("")

    # Calendar
    section = "## 📅 Today's Schedule" if EN else "## 📅 Agenda du jour"
    lines.append(section)
    meeting_events = [e for e in events if not is_ooo_event(e)]
    if meeting_events:
        for ev in meeting_events:
            lines.append(format_event(ev))
    else:
        lines.append("  No meetings today 🎉" if EN else "  Aucune réunion aujourd'hui 🎉")
    lines.append("")

    # Gmail
    section = "## 📧 Emails" if EN else "## 📧 Emails récents"
    lines.append(section)
    unread = get_unread_count(token)
    label = f"  Inbox: **{unread}** unread" if EN else f"  Inbox: **{unread}** non lus"
    lines.append(label)
    emails = get_recent_emails(token, max_results=10, query="newer_than:1d is:unread")
    if emails:
        important_senders = ["smartrecruiters", "jira", "confluence", "slack"]
        priority = [e for e in emails if any(s in e["from"].lower() for s in important_senders)]
        other = [e for e in emails if e not in priority]

        if priority:
            lines.append("  **Priority:**" if EN else "  **Prioritaires:**")
            for e in priority:
                lines.append(format_email(e))
        if other:
            lines.append(f"  **{'Other' if EN else 'Autres'}:** ({len(other)} emails)")
            for e in other[:5]:
                lines.append(format_email(e))
            if len(other) > 5:
                lines.append(f"  ... {'and' if EN else 'et'} {len(other) - 5} {'more' if EN else 'autres'}")
    else:
        lines.append("  No new emails ✅" if EN else "  Aucun nouvel email ✅")
    lines.append("")

    # Jira
    lines.append("## 🎯 Jira")
    blocked = get_blocked_issues()
    if blocked:
        lines.append("  **🔴 Blocked:**" if EN else "  **🔴 Bloqués:**")
        for i in blocked:
            lines.append(format_issue(i))

    issues = get_my_issues()
    if issues:
        in_progress = [i for i in issues if i["status"] in ("In Progress", "In Review")]
        todo = [i for i in issues if i not in in_progress]
        if in_progress:
            lines.append("  **In Progress:**" if EN else "  **En cours:**")
            for i in in_progress:
                lines.append(format_issue(i))
        if todo:
            lines.append(f"  **Backlog:** {len(todo)} ticket{'s' if len(todo) > 1 else ''}")
            for i in todo[:5]:
                lines.append(format_issue(i))
    elif not blocked:
        lines.append("  Jira not configured or no tickets assigned" if EN else "  Jira non configuré ou aucun ticket assigné")
    lines.append("")

    # Board overviews — configure your board keys in jira_api.py
    lines.append("## 📊 Boards")
    for board_key in list_board_keys():
        try:
            overview = get_board_overview(board_key)
            if overview:
                lines.extend(format_board_overview(overview))
                lines.append("")
        except Exception:
            lines.append(f"  ⚠️ Board {board_key}: error fetching data")
    lines.append("")

    # Suggested actions
    lines.append("## ⚡ Suggested Actions" if EN else "## ⚡ Actions suggérées")
    actions = []
    if blocked:
        actions.append(f"- {'Unblock' if EN else 'Débloquer'} {len(blocked)} blocked ticket{'s' if len(blocked) > 1 else ''}")
    if unread > 20:
        actions.append(f"- {'Triage' if EN else 'Trier'} {unread} {'unread emails' if EN else 'emails non lus'}")
    hiring_emails = [e for e in emails if "smartrecruiters" in e["from"].lower()]
    if hiring_emails:
        actions.append(f"- {len(hiring_emails)} SmartRecruiters notification{'s' if len(hiring_emails) > 1 else ''} to action")
    if not actions:
        actions.append("- All clear, have a great day! 🚀" if EN else "- RAS, bonne journée ! 🚀")
    lines.extend(actions)
    lines.append("")

    return "\n".join(lines)


def list_board_keys() -> list[str]:
    """Override this to return your own board keys from jira_api.BOARDS."""
    from jira_api import BOARDS
    return list(BOARDS.keys())


def save_briefing(content: str) -> str:
    os.makedirs(BRIEFING_OUTPUT_DIR, exist_ok=True)
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    filepath = os.path.join(BRIEFING_OUTPUT_DIR, f"{today}-pro.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Daily professional briefing")
    parser.add_argument("--lang", choices=["fr", "en"], default="fr", help="Output language (default: fr)")
    args = parser.parse_args()

    import locale
    if args.lang == "fr":
        try:
            locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
        except locale.Error:
            pass

    result = build_briefing(lang=args.lang)
    if result is None:
        print("📴 No briefing (weekend or full OoO day)")
    else:
        path = save_briefing(result)
        print(result)
        print(f"\n💾 Saved: {path}")


if __name__ == "__main__":
    main()
