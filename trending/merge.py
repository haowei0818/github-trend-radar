"""Merge several Trending boards into one deduplicated list (spec v1.1 §5.3).

- Key: owner/repo, case-insensitive; the first-seen spelling is kept.
- Every board a repo appears on is recorded, in board order.
- stars_this_week is the maximum across boards.
- Order: first appearance, walking boards in the order given.
"""
from dataclasses import dataclass, field

from trending.parser import Repo


@dataclass
class Entry:
    full_name: str
    description: str | None
    language: str | None
    stars_this_week: int | None
    boards: list = field(default_factory=list)
    total_stars: int | None = None
    topics: list | None = None
    created_at: str | None = None
    streak: int | None = None


def merge(boards: dict[str, list[Repo]]) -> list[Entry]:
    by_key: dict[str, Entry] = {}
    for board, repos in boards.items():
        for r in repos:
            key = r.full_name.lower()
            e = by_key.get(key)
            if e is None:
                by_key[key] = Entry(r.full_name, r.description, r.language, r.stars_this_week, [board])
                continue
            if board not in e.boards:
                e.boards.append(board)
            e.stars_this_week = _max(e.stars_this_week, r.stars_this_week)
            e.description = e.description or r.description
            e.language = e.language or r.language
    return list(by_key.values())


def _max(a, b):
    known = [x for x in (a, b) if x is not None]
    return max(known) if known else None
