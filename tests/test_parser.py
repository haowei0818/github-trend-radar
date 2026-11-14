import unittest
from pathlib import Path

from trending.parser import ParseError, Repo, parse_trending

FIXTURE = Path(__file__).parent / "fixtures" / "trending_weekly_2026-11-14.html"


def article(name_html="", desc_html="", lang_html="", stars_html=""):
    """Build one Box-row using the same markup as the real page, for edge cases."""
    return (
        '<article class="Box-row">'
        f'<h2 class="h3 lh-condensed">{name_html}</h2>'
        f"{desc_html}"
        '<div class="f6 color-fg-muted mt-2">'
        f"{lang_html}"
        f"{stars_html}"
        "</div></article>"
    )


NAME = '<a href="/acme/widget" class="Link"><span class="text-normal"> acme / </span> widget</a>'
DESC = '<p class="col-9 color-fg-muted my-1 tmp-pr-4"> A widget </p>'
LANG = '<span><span itemprop="programmingLanguage">Go</span></span>'
STARS = '<span class="d-inline-block float-sm-right"> 1,234 stars this week </span>'


class ParseRealPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repos = parse_trending(FIXTURE.read_text(encoding="utf-8"))

    def test_parses_every_repository_on_page(self):
        self.assertEqual(len(self.repos), 15)

    def test_first_repository_fields(self):
        self.assertEqual(
            self.repos[0],
            Repo(
                full_name="sherlock-project/sherlock",
                description="Hunt down social media accounts by username across social networks",
                language="Python",
                stars_this_week=13364,
            ),
        )

    def test_keeps_page_order(self):
        names = [r.full_name for r in self.repos]
        self.assertEqual(names[1], "anthropics/skills")
        self.assertEqual(names[-1], "lobehub/lobehub")

    def test_non_ascii_description_and_symbol_language(self):
        by_name = {r.full_name: r for r in self.repos}
        self.assertTrue(by_name["ZhuLinsen/daily_stock_analysis"].description.startswith("LLM 驱动"))
        self.assertEqual(by_name["google-deepmind/mujoco"].language, "C++")

    def test_full_names_are_unique_and_well_formed(self):
        names = [r.full_name for r in self.repos]
        self.assertEqual(len(names), len(set(names)))
        for n in names:
            owner, _, repo = n.partition("/")
            self.assertTrue(owner and repo and " " not in n, n)


class ParseEdgeCaseTest(unittest.TestCase):
    def test_missing_description_and_language_become_none(self):
        repos = parse_trending(article(NAME, "", "", STARS))
        self.assertEqual(repos, [Repo("acme/widget", None, None, 1234)])

    def test_missing_stars_this_week_becomes_none(self):
        repos = parse_trending(article(NAME, DESC, LANG, ""))
        self.assertIsNone(repos[0].stars_this_week)

    def test_page_without_repositories_is_an_error(self):
        with self.assertRaises(ParseError):
            parse_trending("<html><body><p>There aren't any trending repositories.</p></body></html>")

    def test_row_without_repository_name_fails_whole_list(self):
        html = article(NAME, DESC, LANG, STARS) + article("", DESC, LANG, STARS)
        with self.assertRaises(ParseError):
            parse_trending(html)


if __name__ == "__main__":
    unittest.main()
