import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from trending.parser import Repo
from trending.snapshot import data_path, week_id, write_snapshot


class WeekIdTest(unittest.TestCase):
    def test_saturday_and_sunday_share_iso_week(self):
        self.assertEqual(week_id(date(2026, 11, 14)), "2026-W46")
        self.assertEqual(week_id(date(2026, 11, 15)), "2026-W46")

    def test_monday_starts_next_week(self):
        self.assertEqual(week_id(date(2026, 11, 16)), "2026-W47")

    def test_new_years_day_can_belong_to_previous_iso_year(self):
        self.assertEqual(week_id(date(2027, 1, 1)), "2026-W53")

    def test_single_digit_week_is_zero_padded(self):
        self.assertEqual(week_id(date(2026, 1, 5)), "2026-W02")

    def test_data_path(self):
        self.assertEqual(data_path(date(2026, 11, 15)), Path("data/2026-W46.json"))


class WriteSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repos = [Repo("acme/widget", "A widget", "Go", 1234)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_week_file_with_meta_and_repos(self):
        path = write_snapshot(self.root, date(2026, 11, 15), self.repos, "2026-11-15T13:00:00Z")
        self.assertEqual(path, self.root / "data" / "2026-W46.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["meta"]["week"], "2026-W46")
        self.assertEqual(data["meta"]["generated_at"], "2026-11-15T13:00:00Z")
        self.assertEqual(
            data["repos"],
            [{"full_name": "acme/widget", "description": "A widget", "language": "Go", "stars_this_week": 1234}],
        )

    def test_rerun_same_week_overwrites_single_file(self):
        write_snapshot(self.root, date(2026, 11, 14), self.repos, "first")
        write_snapshot(self.root, date(2026, 11, 15), [], "second")
        files = list((self.root / "data").iterdir())
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(data["meta"]["generated_at"], "second")
        self.assertEqual(data["repos"], [])

    def test_writes_extra_meta_and_diff(self):
        diff = {"new": ["acme/widget"], "continuing": [], "dropped": ["old/one"]}
        path = write_snapshot(
            self.root, date(2026, 11, 22), self.repos, "t",
            meta={"baseline_week": "2026-W46", "baseline_skipped": []}, diff=diff,
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["meta"]["week"], "2026-W47")
        self.assertEqual(data["meta"]["baseline_week"], "2026-W46")
        self.assertEqual(data["meta"]["baseline_skipped"], [])
        self.assertEqual(data["diff"], diff)

    def test_keeps_non_ascii_readable(self):
        path = write_snapshot(self.root, date(2026, 11, 15), [Repo("a/b", "驱动", None, None)], "t")
        self.assertIn("驱动", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
