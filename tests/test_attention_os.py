import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from attention_os.cli import parse_allocation
from attention_os.engine import (
    AttentionItem,
    LABELS,
    analyze,
    append_capture,
    classify,
    context_freshness_warnings,
    load_context,
    normalize_points,
    render_review,
)


class AttentionEngineTests(unittest.TestCase):
    def test_normalize_points_always_totals_100(self):
        points = normalize_points({"delivery": 3, "people": 2, "support": 1})
        self.assertEqual(sum(points.values()), 100)
        self.assertEqual(points["delivery"], 50)

    def test_classification_is_transparent_and_deterministic(self):
        self.assertEqual(classify("1:1 career feedback with Alice"), "people")
        self.assertEqual(classify("Production incident triage"), "support")
        self.assertEqual(classify("Architecture quality review"), "technical_direction")
        self.assertEqual(classify("Next-year strategy workshop"), "team_future")
        self.assertEqual(classify("Onboarding et passation de Cédric"), "people")
        self.assertEqual(classify("Pilote IA et sondage équipe"), "team_future")

    def test_analysis_flags_concentration_and_attention_floor(self):
        report = analyze(
            [
                AttentionItem("Sprint planning", 180, "delivery"),
                AttentionItem("One on one", 30, "people"),
            ],
            report_date=date(2026, 9, 10),
        )
        self.assertEqual(sum(report.planned.values()), 100)
        self.assertEqual(report.dominant_category, "delivery")
        self.assertTrue(any("concentration" in item for item in report.warnings))
        self.assertIn(
            LABELS[report.underinvested_category].lower(),
            report.letter_block,
        )

    def test_context_loader_ignores_completed_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "weekly-focus.md").write_text(
                "| # | Priorité | Status | Notes |\n"
                "|---|---|---|---|\n"
                "| 1 | Strategy workshop | open | |\n"
                "| 2 | Finished release | done | |\n",
                encoding="utf-8",
            )
            (root / "open-loops.md").write_text(
                "| ID | Description | Due | Added | Status |\n"
                "|---|---|---|---|---|\n"
                "| OL-1 | 1:1 feedback | 2026-09-01 | 2026-08-01 | open |\n"
                "| OL-2 | Closed incident | 2026-09-01 | 2026-08-01 | done |\n",
                encoding="utf-8",
            )
            items = load_context(root)
        self.assertEqual(len(items), 2)
        self.assertEqual({item.category for item in items}, {"people", "team_future"})

    def test_capture_and_review_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "journal.jsonl"
            append_capture(
                journal,
                actual=parse_allocation(
                    "delivery=40,people=20,support=10,"
                    "technical_direction=20,team_future=10"
                ),
                energy=4,
                win="Protected a coaching block",
                adjustment="Reduce delivery status meetings",
                capture_date=date(2026, 9, 10),
            )
            record = json.loads(journal.read_text(encoding="utf-8"))
            review = render_review(journal)
        self.assertEqual(sum(record["actual"].values()), 100)
        self.assertIn("Average energy: **4.0/5**", review)
        self.assertIn("Reduce delivery status meetings", review)

    def test_stale_context_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "weekly-focus.md").write_text(
                "# Weekly Focus — Semaine du 2026-07-01\n",
                encoding="utf-8",
            )
            warnings = context_freshness_warnings(
                root,
                today=date(2026, 9, 10),
            )
        self.assertEqual(len(warnings), 1)
        self.assertIn("weekly-focus.md", warnings[0])


if __name__ == "__main__":
    unittest.main()
