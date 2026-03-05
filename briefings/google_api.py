"""Google API helpers for Calendar and Gmail."""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, TIMEZONE


def get_access_token(refresh_token: str) -> str:
    data = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def _api_get(url: str, access_token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


# --- Calendar ---

def get_today_events(access_token: str, calendar_id: str = "primary") -> list[dict]:
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    params = urllib.parse.urlencode({
        "timeMin": start_of_day.isoformat(),
        "timeMax": end_of_day.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 50,
    })
    url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events?{params}"
    data = _api_get(url, access_token)
    return data.get("items", [])


def is_ooo_all_day(events: list[dict]) -> bool:
    """Check if there's an OoO/vacation event covering the full day."""
    for ev in events:
        summary = (ev.get("summary") or "").lower()
        ooo_keywords = ["ooo", "out of office", "vacances", "vacation", "congé", "congés", "absent", "off"]
        if any(kw in summary for kw in ooo_keywords):
            start = ev.get("start", {})
            if start.get("date"):
                return True
            if start.get("dateTime"):
                from datetime import datetime as dt
                s = dt.fromisoformat(start["dateTime"])
                e = dt.fromisoformat(ev["end"]["dateTime"])
                if (e - s).total_seconds() >= 8 * 3600:
                    return True
    return False


def is_ooo_afternoon_only(events: list[dict]) -> bool:
    """Check if OoO is only in the afternoon (briefing should still run)."""
    for ev in events:
        summary = (ev.get("summary") or "").lower()
        ooo_keywords = ["ooo", "out of office", "vacances", "vacation", "congé", "congés", "absent", "off"]
        if any(kw in summary for kw in ooo_keywords):
            start = ev.get("start", {})
            if start.get("dateTime"):
                from datetime import datetime as dt
                s = dt.fromisoformat(start["dateTime"])
                if s.hour >= 12:
                    return True
    return False


def format_event(ev: dict) -> str:
    start = ev.get("start", {})
    summary = ev.get("summary", "(no title)")
    if start.get("date"):
        return f"  📅 All day — {summary}"
    if start.get("dateTime"):
        t = datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
        end_t = datetime.fromisoformat(ev["end"]["dateTime"]).strftime("%H:%M")
        return f"  🕐 {t}-{end_t} — {summary}"
    return f"  📅 {summary}"


# --- Gmail ---

def get_recent_emails(access_token: str, max_results: int = 15, query: str = "newer_than:1d") -> list[dict]:
    params = urllib.parse.urlencode({
        "maxResults": max_results,
        "q": query,
    })
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{params}"
    data = _api_get(url, access_token)
    messages = data.get("messages", [])

    results = []
    for msg in messages[:max_results]:
        detail = _api_get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date",
            access_token,
        )
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        labels = detail.get("labelIds", [])
        results.append({
            "id": msg["id"],
            "from": headers.get("From", "?"),
            "subject": headers.get("Subject", "(no subject)"),
            "date": headers.get("Date", "?"),
            "unread": "UNREAD" in labels,
            "labels": labels,
        })
    return results


def get_unread_count(access_token: str) -> int:
    url = "https://gmail.googleapis.com/gmail/v1/users/me/labels/INBOX"
    data = _api_get(url, access_token)
    return data.get("messagesUnread", 0)


def format_email(email: dict) -> str:
    flag = "🔴" if email["unread"] else "  "
    sender = email["from"].split("<")[0].strip().strip('"')
    return f"  {flag} {sender} — {email['subject']}"
