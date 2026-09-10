"""Deterministic attention-budget analysis for engineering managers."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

CATEGORIES = (
    "delivery",
    "people",
    "support",
    "technical_direction",
    "team_future",
)

LABELS = {
    "delivery": "Delivery",
    "people": "People",
    "support": "Support",
    "technical_direction": "Technical direction",
    "team_future": "Team future",
}

KEYWORDS = {
    "delivery": (
        "delivery", "daily", "standup", "sprint", "planning", "refinement",
        "release", "project", "okr", "milestone", "demo", "showtime",
        "livraison", "quotidien", "planification", "jalon", "démo", "projet",
    ),
    "people": (
        "1:1", "one on one", "feedback", "career", "performance", "hiring",
        "interview", "onboarding", "people", "team health",
        "carrière", "entretien", "recrutement", "intégration", "équipe",
        "profil", "direct report", "passation",
    ),
    "support": (
        "support", "incident", "alert", "blocked", "urgent", "on-call",
        "customer care", "triage", "production", "outage",
        "assistance", "alerte", "bloqué", "urgence", "astreinte", "panne",
    ),
    "technical_direction": (
        "architecture", "technical", "quality", "design doc", "sdd", "rfc",
        "tech debt", "reliability", "security", "platform",
        "technique", "qualité", "dette", "fiabilité", "sécurité", "plateforme",
    ),
    "team_future": (
        "strategy", "roadmap", "future", "vision", "workshop", "offsite",
        "organization", "organisation", "capacity", "budget", "succession",
        "stratégie", "feuille de route", "avenir", "atelier", "capacité",
        "sondage", "pilote", "innovation", "ia ",
    ),
}

DEFAULT_TARGET = {
    "delivery": 25,
    "people": 25,
    "support": 15,
    "technical_direction": 20,
    "team_future": 15,
}


@dataclass(frozen=True)
class AttentionItem:
    title: str
    minutes: int
    category: str
    source: str = "manual"


@dataclass(frozen=True)
class AttentionReport:
    report_date: str
    planned: dict[str, int]
    target: dict[str, int]
    gap: dict[str, int]
    dominant_category: str
    underinvested_category: str
    letter_block: str
    warnings: list[str]
    items: list[AttentionItem]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["items"] = [asdict(item) for item in self.items]
        return payload


def classify(text: str) -> str:
    """Classify text into one attention category using transparent keywords."""
    normalized = text.casefold()
    scores = {
        category: sum(1 for keyword in keywords if keyword in normalized)
        for category, keywords in KEYWORDS.items()
    }
    best = max(CATEGORIES, key=lambda category: (scores[category], -CATEGORIES.index(category)))
    return best if scores[best] else "delivery"


def normalize_points(values: dict[str, float]) -> dict[str, int]:
    """Normalize non-negative values to exactly 100 integer points."""
    cleaned = {category: max(0.0, float(values.get(category, 0))) for category in CATEGORIES}
    total = sum(cleaned.values())
    if total <= 0:
        return dict(DEFAULT_TARGET)

    raw = {category: value * 100 / total for category, value in cleaned.items()}
    points = {category: int(value) for category, value in raw.items()}
    remainder = 100 - sum(points.values())
    order = sorted(
        CATEGORIES,
        key=lambda category: raw[category] - points[category],
        reverse=True,
    )
    for category in order[:remainder]:
        points[category] += 1
    return points


def load_calendar(path: Path | None) -> list[AttentionItem]:
    """Load a portable JSON calendar export.

    Expected shape: [{"title": "...", "duration_minutes": 30, "category": "people"}].
    Category is optional and inferred from the title when absent.
    """
    if path is None or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items: list[AttentionItem] = []
    for row in data:
        title = str(row.get("title", "Untitled event"))
        category = row.get("category") or classify(title)
        if category not in CATEGORIES:
            raise ValueError(f"Unknown attention category: {category}")
        items.append(
            AttentionItem(
                title=title,
                minutes=max(1, int(row.get("duration_minutes", 30))),
                category=category,
                source="calendar",
            )
        )
    return items


def _markdown_rows(path: Path) -> Iterable[list[str]]:
    if not path.exists():
        return []
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or re.match(r"^\|[\s\-:|]+\|$", stripped):
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return rows


def load_context(context_dir: Path | None) -> list[AttentionItem]:
    """Extract workload signals from Chief-of-Staff Markdown files."""
    if context_dir is None:
        return []

    items: list[AttentionItem] = []
    focus_rows = list(_markdown_rows(context_dir / "weekly-focus.md"))
    for row in focus_rows[1:]:
        if len(row) >= 3 and row[0].isdigit() and "done" not in row[2].casefold():
            title = row[1]
            items.append(
                AttentionItem(title=title, minutes=60, category=classify(title), source="weekly_focus")
            )

    loop_rows = list(_markdown_rows(context_dir / "open-loops.md"))
    today = date.today()
    for row in loop_rows[1:]:
        if len(row) < 5 or not row[0].startswith("OL-"):
            continue
        if row[4].casefold() in {"done", "closed", "cancelled"}:
            continue
        title = row[1]
        minutes = 45
        try:
            due = date.fromisoformat(row[2])
            if due <= today:
                minutes = 90
        except ValueError:
            pass
        items.append(
            AttentionItem(title=title, minutes=minutes, category=classify(title), source="open_loop")
        )
    return items


def context_freshness_warnings(
    context_dir: Path | None,
    *,
    today: date | None = None,
    max_age_days: int = 14,
) -> list[str]:
    """Warn when dated context metadata is too old for daily decisions."""
    if context_dir is None:
        return []
    current = today or date.today()
    checks = (
        ("weekly-focus.md", r"Semaine du\s+(\d{4}-\d{2}-\d{2})"),
        ("context.md", r"Last updated:\s*(\d{4}-\d{2}-\d{2})"),
        ("agenda-manual.md", r"Dernière MAJ\s*:\s*\**(\d{4}-\d{2}-\d{2})"),
    )
    warnings: list[str] = []
    for filename, pattern in checks:
        path = context_dir / filename
        if not path.exists():
            continue
        match = re.search(pattern, path.read_text(encoding="utf-8"), re.IGNORECASE)
        if not match:
            continue
        source_date = date.fromisoformat(match.group(1))
        age = (current - source_date).days
        if age > max_age_days:
            warnings.append(
                f"{filename} is {age} days old; refresh it before relying on this allocation."
            )
    return warnings


def build_target(items: Iterable[AttentionItem]) -> dict[str, int]:
    """Adapt the baseline target to current risk signals, then normalize."""
    values = {category: float(points) for category, points in DEFAULT_TARGET.items()}
    for item in items:
        if item.source == "open_loop":
            values[item.category] += 3
        elif item.source == "weekly_focus":
            values[item.category] += 2
    return normalize_points(values)


def analyze(
    items: list[AttentionItem],
    *,
    target: dict[str, int] | None = None,
    report_date: date | None = None,
) -> AttentionReport:
    target_points = normalize_points(target or build_target(items))
    planned_points = normalize_points(
        {
            category: sum(item.minutes for item in items if item.category == category)
            for category in CATEGORIES
        }
    )
    gap = {
        category: planned_points[category] - target_points[category]
        for category in CATEGORIES
    }
    dominant = max(CATEGORIES, key=lambda category: planned_points[category])
    underinvested = min(CATEGORIES, key=lambda category: gap[category])

    warnings: list[str] = []
    if planned_points[dominant] >= 60:
        warnings.append(
            f"{LABELS[dominant]} consumes {planned_points[dominant]} points; "
            "the day has a single-area concentration risk."
        )
    for category in CATEGORIES:
        if planned_points[category] < 10:
            warnings.append(
                f"{LABELS[category]} is below the 10-point attention floor "
                f"({planned_points[category]})."
            )

    letter_block = (
        f"Protect 60–90 minutes for {LABELS[underinvested].lower()}: "
        "use it for judgment, coaching, or synthesis—not status administration."
    )
    return AttentionReport(
        report_date=(report_date or date.today()).isoformat(),
        planned=planned_points,
        target=target_points,
        gap=gap,
        dominant_category=dominant,
        underinvested_category=underinvested,
        letter_block=letter_block,
        warnings=warnings,
        items=items,
    )


def render_markdown(report: AttentionReport) -> str:
    lines = [
        f"# EM Attention Brief — {report.report_date}",
        "",
        "> 100 attention points across Delivery, People, Support, "
        "Technical direction, and Team future.",
        "",
        "## Attention budget",
        "",
        "| Area | Planned | Target | Gap |",
        "|---|---:|---:|---:|",
    ]
    for category in CATEGORIES:
        gap = report.gap[category]
        lines.append(
            f"| {LABELS[category]} | {report.planned[category]} | "
            f"{report.target[category]} | {gap:+d} |"
        )

    lines += ["", "## Signals", ""]
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- No concentration or attention-floor warning.")

    lines += [
        "",
        "## Letter block",
        "",
        f"> **{report.letter_block}**",
        "",
        "## Inputs",
        "",
    ]
    if report.items:
        lines.extend(
            f"- [{LABELS[item.category]} · {item.minutes}m] {item.title} ({item.source})"
            for item in report.items
        )
    else:
        lines.append("- No calendar/context items supplied; baseline target shown.")

    lines += [
        "",
        "## End-of-day capture",
        "",
        "Record actual points, energy (1–5), one win, and one adjustment:",
        "",
        "```bash",
        "python -m attention_os capture --actual "
        "delivery=25,people=25,support=15,technical_direction=20,team_future=15 "
        "--energy 3 --win \"...\" --adjustment \"...\"",
        "```",
        "",
    ]
    return "\n".join(lines)


def append_capture(
    journal_path: Path,
    *,
    actual: dict[str, int],
    energy: int,
    win: str,
    adjustment: str,
    capture_date: date | None = None,
) -> dict:
    if energy not in range(1, 6):
        raise ValueError("Energy must be between 1 and 5")
    normalized = normalize_points(actual)
    record = {
        "date": (capture_date or date.today()).isoformat(),
        "actual": normalized,
        "energy": energy,
        "win": win.strip(),
        "adjustment": adjustment.strip(),
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def render_review(journal_path: Path, days: int = 7) -> str:
    if not journal_path.exists():
        return "# EM Attention Review\n\n_No captures yet._\n"
    records = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][-days:]
    if not records:
        return "# EM Attention Review\n\n_No captures yet._\n"

    averages = {
        category: round(sum(row["actual"][category] for row in records) / len(records))
        for category in CATEGORIES
    }
    energy = sum(row["energy"] for row in records) / len(records)
    dominant = max(CATEGORIES, key=lambda category: averages[category])
    neglected = min(CATEGORIES, key=lambda category: averages[category])

    lines = [
        f"# EM Attention Review — last {len(records)} captures",
        "",
        f"- Average energy: **{energy:.1f}/5**",
        f"- Dominant area: **{LABELS[dominant]} ({averages[dominant]} points)**",
        f"- Lowest area: **{LABELS[neglected]} ({averages[neglected]} points)**",
        "",
        "## Average allocation",
        "",
        "| Area | Points |",
        "|---|---:|",
    ]
    lines.extend(f"| {LABELS[c]} | {averages[c]} |" for c in CATEGORIES)
    lines += ["", "## Adjustments", ""]
    adjustments = [row["adjustment"] for row in records if row.get("adjustment")]
    lines.extend(f"- {item}" for item in adjustments[-5:])
    return "\n".join(lines) + "\n"
