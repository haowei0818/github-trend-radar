import json
import tempfile
import unittest
from pathlib import Path

from trending.diff import apply_diff, find_baseline
from trending.merge import Entry


def entry(name):
    return Entry(name, "d", "Python", 10, ["all"])


def base(name, streak=None):
    r = {"full_name": name}
    if streak is not None:
        r["streak"] = streak
    return r


class ApplyDiffTest(unittest.TestCase):
    def test_first_period_everything_is_new_with_streak_one(self):
        cur = [entry("a/x"), entry("b/y")]
        diff = apply_diff(cur, None)
        self.assertEqual(diff, {"new": ["a/x", "b/y"], "continuing": [], "dropped": []})
        self.assertEqual([e.streak for e in cur], [1, 1])

    def test_three_lists_match_hand_computed_result(self):
        cur = [entry("keep/one"), entry("fresh/two"), entry("keep/three")]
        prev = [base("keep/one", 1), base("gone/four", 2), base("keep/three", 1)]
        diff = apply_diff(cur, prev)
        self.assertEqual(diff["new"], ["fresh/two"])
        self.assertEqual(diff["continuing"], ["keep/one", "keep/three"])
        self.assertEqual(diff["dropped"], ["gone/four"])

    def test_streak_increments_from_baseline(self):
        cur = [entry("a/x")]
        apply_diff(cur, [base("a/x", 2)])
        self.assertEqual(cur[0].streak, 3)

    def test_baseline_without_streak_field_counts_as_one(self):
        # W46 data files were written before streak existed.
        cur = [entry("a/x")]
        apply_diff(cur, [base("a/x")])
        self.assertEqual(cur[0].streak, 2)

    def test_matching_is_case_insensitive(self):
        cur = [entry("Acme/Widget")]
        diff = apply_diff(cur, [base("acme/widget", 1)])
        self.assertEqual(diff["continuing"], ["Acme/Widget"])
        self.assertEqual(diff["dropped"], [])
        self.assertEqual(cur[0].streak, 2)

    def test_case_change_in_baseline_is_not_reported_as_dropped(self):
        diff = apply_diff([entry("acme/widget")], [base("ACME/Widget", 1)])
        self.assertEqual(diff["dropped"], [])
        self.assertEqual(diff["continuing"], ["acme/widget"])

    def test_new_repo_gets_streak_one_even_when_baseline_exists(self):
        cur = [entry("n/new")]
        apply_diff(cur, [base("o/old", 5)])
        self.assertEqual(cur[0].streak, 1)


def write(dir_, week, payload):
    p = dir_ / f"{week}.json"
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")


def good(names):
    return {"meta": {}, "repos": [base(n, 1) for n in names]}


class FindBaselineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_directory_means_first_period(self):
        self.assertEqual(find_baseline(self.dir / "nope", "2026-W47"), (None, None, []))

    def test_picks_previous_week_and_ignores_current_week_file(self):
        write(self.dir, "2026-W45", good(["old/a"]))
        write(self.dir, "2026-W46", good(["prev/b"]))
        write(self.dir, "2026-W47", good(["cur/c"]))
        week, repos, skipped = find_baseline(self.dir, "2026-W47")
        self.assertEqual(week, "2026-W46")
        self.assertEqual([r["full_name"] for r in repos], ["prev/b"])
        self.assertEqual(skipped, [])

    def test_falls_back_to_week_before_last_when_last_week_missing(self):
        write(self.dir, "2026-W45", good(["older/a"]))
        week, _, skipped = find_baseline(self.dir, "2026-W47")
        self.assertEqual(week, "2026-W45")
        self.assertEqual(skipped, [])

    def test_corrupted_previous_file_is_skipped_and_reported(self):
        write(self.dir, "2026-W45", good(["older/a"]))
        write(self.dir, "2026-W46", "{not json")
        week, _, skipped = find_baseline(self.dir, "2026-W47")
        self.assertEqual(week, "2026-W45")
        self.assertEqual(skipped, ["2026-W46"])

    def test_file_without_repo_list_counts_as_corrupted(self):
        write(self.dir, "2026-W45", good(["older/a"]))
        write(self.dir, "2026-W46", {"meta": {}})
        week, _, skipped = find_baseline(self.dir, "2026-W47")
        self.assertEqual((week, skipped), ("2026-W45", ["2026-W46"]))

    def test_only_corrupted_files_means_no_baseline(self):
        write(self.dir, "2026-W46", "garbage")
        self.assertEqual(find_baseline(self.dir, "2026-W47"), (None, None, ["2026-W46"]))

    def test_year_boundary_ordering(self):
        write(self.dir, "2026-W52", good(["a/a"]))
        write(self.dir, "2026-W53", good(["b/b"]))
        self.assertEqual(find_baseline(self.dir, "2027-W01")[0], "2026-W53")

    def test_ignores_non_week_files(self):
        write(self.dir, "2026-W46", good(["a/a"]))
        (self.dir / "notes.json").write_text("{}", encoding="utf-8")
        (self.dir / "2026-W46.json.tmp").write_text("x", encoding="utf-8")
        self.assertEqual(find_baseline(self.dir, "2026-W47")[0], "2026-W46")


if __name__ == "__main__":
    unittest.main()
