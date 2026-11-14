"""Parse a GitHub Trending page into Repo records.

Spec v1.1 §6.1: a row without a repository name invalidates the whole list;
missing secondary fields (description, language, stars this week) become None.
"""
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


class ParseError(Exception):
    """The page cannot be trusted as a Trending list."""


@dataclass(frozen=True)
class Repo:
    full_name: str
    description: str | None
    language: str | None
    stars_this_week: int | None


_STARS_RE = re.compile(r"([\d,]+)\s+stars?\s+this\s+week", re.IGNORECASE)


def parse_trending(html: str) -> list[Repo]:
    rows = BeautifulSoup(html, "html.parser").select("article.Box-row")
    if not rows:
        raise ParseError("no repository rows found")
    return [_parse_row(i, row) for i, row in enumerate(rows, start=1)]


def _parse_row(index, row) -> Repo:
    link = row.select_one("h2 a[href]")
    full_name = link["href"].strip("/") if link else ""
    if full_name.count("/") != 1:
        raise ParseError(f"row {index}: repository name not found")

    desc_el = row.find("p")
    lang_el = row.select_one('[itemprop="programmingLanguage"]')
    return Repo(
        full_name=full_name,
        description=_text(desc_el),
        language=_text(lang_el),
        stars_this_week=_stars_this_week(row.get_text(" ")),
    )


def _text(el) -> str | None:
    if el is None:
        return None
    text = " ".join(el.get_text(" ").split())
    return text or None


def _stars_this_week(text: str) -> int | None:
    m = _STARS_RE.search(text)
    return int(m.group(1).replace(",", "")) if m else None
