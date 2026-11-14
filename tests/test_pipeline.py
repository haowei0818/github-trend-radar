"""Spec v1.1 §6.1 — failure handling of the whole data pipeline, with injected I/O."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from trending.pipeline import BOARDS, run

FIXTURE = (Path(__file__).parent / "fixtures" / "trending_weekly_2026-11-14.html").read_text(encoding="utf-8")
TODAY = date(2026, 11, 15)  # 2026-W46


def page(*names, stars=True):
    rows = "".join(
        '<article class="Box-row">'
        f'<h2><a href="/{n}">{n}</a></h2><p>desc</p>'
        '<div><span itemprop="programmingLanguage">Go</span>'
        + ('<span> 10 stars this week </span>' if stars else "")
        + "</div></article>"
        for n in names
    )
    return f"<html><body>{rows}</body></html>"


PAGES = {
    "all": FIXTURE,
    "python": page("py/one", "anthropics/skills"),
    "typescript": page("ts/one"),
    "go": page("go/one"),
}


class Fetcher:
    def __init__(self, pages=PAGES, fail=()):
        self.pages, self.fail = pages, set(fail)

    def __call__(self, url):
        board = next(b for b, u in BOARDS.items() if u == url)
        if board in self.fail:
            raise OSError(f"HTTP 503 for {board}")
        return self.pages[board]


class Client:
    def __init__(self, fail=(), flaky=()):
        self.fail, self.flaky, self.calls = set(fail), set(flaky), {}

    def __call__(self, name):
        n = self.calls[name] = self.calls.get(name, 0) + 1
        if name in self.fail or (name in self.flaky and n == 1):
            raise OSError("rate limited")
        return {"stargazers_count": 1, "topics": ["t"], "created_at": "2025-01-01T00:00:00Z"}


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, fetch=None, client=None):
        return run(fetch or Fetcher(), client or Client(), self.root, TODAY, "now", sleep=lambda s: None)

    def data(self):
        return json.loads((self.root / "data" / "2026-W46.json").read_text(encoding="utf-8"))

    # --- happy path -------------------------------------------------------
    def test_all_ok_writes_file_without_degradations(self):
        result = self.go()
        self.assertTrue(result.ok)
        meta = self.data()["meta"]
        self.assertEqual(meta["boards"], {b: "ok" for b in BOARDS})
        self.assertEqual(meta["degradations"], [])
        self.assertEqual(len(self.data()["repos"]), 15 + 1 + 1 + 1)  # anthropics/skills deduped

    # --- all-language board is mandatory -----------------------------------
    def test_all_language_fetch_failure_writes_nothing(self):
        result = self.go(fetch=Fetcher(fail={"all"}))
        self.assertFalse(result.ok)
        self.assertIn("all", result.reason)
        self.assertFalse((self.root / "data").exists())

    def test_all_language_parse_failure_does_not_overwrite_existing_file(self):
        self.go()
        before = (self.root / "data" / "2026-W46.json").read_text(encoding="utf-8")
        result = self.go(fetch=Fetcher(pages={**PAGES, "all": "<html>empty</html>"}))
        self.assertFalse(result.ok)
        self.assertEqual((self.root / "data" / "2026-W46.json").read_text(encoding="utf-8"), before)

    # --- language boards degrade -------------------------------------------
    def test_language_board_fetch_failure_degrades(self):
        result = self.go(fetch=Fetcher(fail={"go"}))
        self.assertTrue(result.ok)
        meta = self.data()["meta"]
        self.assertEqual(meta["boards"]["go"], "failed")
        self.assertEqual(meta["boards"]["python"], "ok")
        self.assertTrue(any("go" in d for d in meta["degradations"]))
        self.assertNotIn("go/one", [r["full_name"] for r in self.data()["repos"]])

    def test_language_board_parse_failure_degrades(self):
        self.go(fetch=Fetcher(pages={**PAGES, "typescript": "<html>changed layout</html>"}))
        meta = self.data()["meta"]
        self.assertEqual(meta["boards"]["typescript"], "failed")
        self.assertTrue(any("typescript" in d for d in meta["degradations"]))

    # --- secondary fields ---------------------------------------------------
    def test_missing_stars_this_week_is_recorded(self):
        self.go(fetch=Fetcher(pages={**PAGES, "go": page("go/one", stars=False)}))
        self.assertTrue(any("stars this week" in d and "go/one" in d for d in self.data()["meta"]["degradations"]))

    # --- REST API -----------------------------------------------------------
    def test_api_is_retried_before_giving_up(self):
        client = Client(flaky={"go/one"})
        self.go(client=client)
        self.assertEqual(client.calls["go/one"], 2)
        go_one = next(r for r in self.data()["repos"] if r["full_name"] == "go/one")
        self.assertEqual(go_one["total_stars"], 1)
        self.assertEqual(self.data()["meta"]["degradations"], [])

    def test_api_failure_after_retries_marks_unknown_and_degrades(self):
        client = Client(fail={"go/one"})
        self.go(client=client)
        self.assertEqual(client.calls["go/one"], 3)  # 1 try + 2 retries
        go_one = next(r for r in self.data()["repos"] if r["full_name"] == "go/one")
        self.assertIsNone(go_one["total_stars"])
        self.assertTrue(any("go/one" in d for d in self.data()["meta"]["degradations"]))

    # --- baseline -----------------------------------------------------------
    def test_corrupted_baseline_is_recorded_as_degradation(self):
        (self.root / "data").mkdir()
        (self.root / "data" / "2026-W45.json").write_text("{broken", encoding="utf-8")
        self.go()
        meta = self.data()["meta"]
        self.assertEqual(meta["baseline_skipped"], ["2026-W45"])
        self.assertTrue(any("2026-W45" in d for d in meta["degradations"]))

    def test_never_substitutes_search_api_for_trending(self):
        # The only network calls allowed for repo lists are the four Trending URLs.
        seen = []

        def fetch(url):
            seen.append(url)
            return Fetcher()(url)

        self.go(fetch=fetch)
        self.assertEqual(sorted(seen), sorted(BOARDS.values()))


if __name__ == "__main__":
    unittest.main()
