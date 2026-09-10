"""Command-line interface for the EM Attention Operating System."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from .engine import (
    CATEGORIES,
    analyze,
    append_capture,
    context_freshness_warnings,
    load_calendar,
    load_context,
    render_markdown,
    render_review,
)

DEFAULT_STATE_DIR = Path.home() / ".em-attention-os"


def parse_allocation(value: str) -> dict[str, int]:
    allocation: dict[str, int] = {}
    for pair in value.split(","):
        if "=" not in pair:
            raise argparse.ArgumentTypeError(f"Expected category=points, got: {pair}")
        category, points = pair.split("=", 1)
        category = category.strip()
        if category not in CATEGORIES:
            raise argparse.ArgumentTypeError(
                f"Unknown category {category!r}; use {', '.join(CATEGORIES)}"
            )
        try:
            allocation[category] = int(points)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid points in: {pair}") from exc
    return allocation


def _write_or_print(content: str, output: str | None) -> None:
    if output:
        path = Path(output).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Saved: {path}")
    else:
        print(content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="em-attention",
        description="Make an engineering manager's 100-point attention budget explicit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    daily = sub.add_parser("daily", help="Generate today's attention brief")
    daily.add_argument("--context-dir", help="Chief-of-Staff Markdown directory")
    daily.add_argument("--calendar-json", help="Portable calendar JSON file")
    daily.add_argument("--target", type=parse_allocation, help="Custom target allocation")
    daily.add_argument("--date", help="Report date (YYYY-MM-DD)")
    daily.add_argument("--output", help="Write Markdown report to this path")
    daily.add_argument("--json-output", help="Also write machine-readable report JSON")

    capture = sub.add_parser("capture", help="Record an end-of-day attention check-in")
    capture.add_argument("--actual", type=parse_allocation, required=True)
    capture.add_argument("--energy", type=int, required=True)
    capture.add_argument("--win", default="")
    capture.add_argument("--adjustment", default="")
    capture.add_argument("--date", help="Capture date (YYYY-MM-DD)")
    capture.add_argument(
        "--journal",
        default=str(DEFAULT_STATE_DIR / "journal.jsonl"),
        help="Private JSONL journal path",
    )

    review = sub.add_parser("review", help="Review recent attention captures")
    review.add_argument("--days", type=int, default=7)
    review.add_argument(
        "--journal",
        default=str(DEFAULT_STATE_DIR / "journal.jsonl"),
        help="Private JSONL journal path",
    )
    review.add_argument("--output", help="Write Markdown review to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "daily":
        context_dir = (
            Path(args.context_dir).expanduser() if args.context_dir else None
        )
        items = load_calendar(
            Path(args.calendar_json).expanduser() if args.calendar_json else None
        )
        items += load_context(context_dir)
        report_date = date.fromisoformat(args.date) if args.date else None
        report = analyze(
            items,
            target=args.target,
            report_date=report_date,
        )
        freshness = context_freshness_warnings(
            context_dir,
            today=report_date,
        )
        if freshness:
            report = replace(report, warnings=freshness + report.warnings)
        _write_or_print(render_markdown(report), args.output)
        if args.json_output:
            path = Path(args.json_output).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"Saved: {path}")
        return 0

    if args.command == "capture":
        record = append_capture(
            Path(args.journal).expanduser(),
            actual=args.actual,
            energy=args.energy,
            win=args.win,
            adjustment=args.adjustment,
            capture_date=date.fromisoformat(args.date) if args.date else None,
        )
        print(
            f"Captured {record['date']}: energy {record['energy']}/5, "
            f"100 attention points."
        )
        return 0

    if args.days < 1:
        raise SystemExit("--days must be at least 1")
    _write_or_print(
        render_review(Path(args.journal).expanduser(), args.days),
        args.output,
    )
    return 0
