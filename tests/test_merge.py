import unittest

from trending.merge import Entry, merge
from trending.parser import Repo


def repo(name, stars=100, desc="d", lang="Python"):
    return Repo(name, desc, lang, stars)


class MergeTest(unittest.TestCase):
    def test_single_board_keeps_order_and_records_board(self):
        out = merge({"all": [repo("a/one"), repo("b/two")]})
        self.assertEqual([e.full_name for e in out], ["a/one", "b/two"])
        self.assertEqual(out[0].boards, ["all"])

    def test_same_repo_on_two_boards_appears_once_with_both_boards(self):
        out = merge({"all": [repo("acme/widget", 500)], "python": [repo("acme/widget", 500)]})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].boards, ["all", "python"])

    def test_dedupe_is_case_insensitive_and_keeps_first_seen_name(self):
        out = merge({"all": [repo("Acme/Widget")], "go": [repo("acme/widget")]})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].full_name, "Acme/Widget")
        self.assertEqual(out[0].boards, ["all", "go"])

    def test_stars_this_week_takes_maximum_across_boards(self):
        out = merge({"all": [repo("a/x", 300)], "python": [repo("a/x", 450)], "go": [repo("a/x", 200)]})
        self.assertEqual(out[0].stars_this_week, 450)

    def test_missing_stars_on_one_board_does_not_hide_known_value(self):
        out = merge({"all": [repo("a/x", None)], "python": [repo("a/x", 120)]})
        self.assertEqual(out[0].stars_this_week, 120)

    def test_first_seen_fills_missing_description_and_language_from_later_board(self):
        out = merge({"all": [Repo("a/x", None, None, 1)], "go": [Repo("a/x", "desc", "Go", 1)]})
        self.assertEqual((out[0].description, out[0].language), ("desc", "Go"))

    def test_new_repos_from_later_boards_append_after_earlier_ones(self):
        out = merge({"all": [repo("a/x")], "python": [repo("a/x"), repo("p/y")], "go": [repo("g/z")]})
        self.assertEqual([e.full_name for e in out], ["a/x", "p/y", "g/z"])

    def test_merged_count_never_exceeds_total_input(self):
        boards = {"all": [repo("a/x"), repo("b/y")], "python": [repo("A/X"), repo("c/z")]}
        out = merge(boards)
        self.assertEqual(len(out), 3)
        self.assertLessEqual(len(out), sum(len(v) for v in boards.values()))

    def test_enrichment_fields_start_unknown(self):
        e = merge({"all": [repo("a/x")]})[0]
        self.assertIsInstance(e, Entry)
        self.assertEqual((e.total_stars, e.topics, e.created_at), (None, None, None))


if __name__ == "__main__":
    unittest.main()
