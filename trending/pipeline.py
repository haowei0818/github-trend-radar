"""The whole weekly data pipeline behind one function (spec v1.1 §5.2, §6.1).

All I/O is injected — `fetch(url) -> html`, `client(full_name) -> dict`, `sleep(s)` —
so every failure mode is unit-testable.

Failure policy:
- all-language board fails (network or parse) -> no file written, result.ok False
- a language board fails                       -> board marked "failed", degradation recorded
- stars-this-week missing on some rows         -> degradation recorded
- REST lookup fails after retries              -> fields unknown, degradation recorded
- corrupted earlier data files                 -> skipped, degradation recorded
Repo lists come only from the Trending pages; nothing substitutes for them.
"""
from dataclasses import dataclass
from pathlib import Path

from trending.diff import apply_diff, find_baseline
from trending.enrich import enrich
from trending.merge import merge
from trending.parser import ParseError, parse_trending
from trending.snapshot import week_id, write_snapshot

BOARDS = {
    "all": "https://github.com/trending?since=weekly",
    "python": "https://github.com/trending/python?since=weekly",
    "typescript": "https://github.com/trending/typescript?since=weekly",
    "go": "https://github.com/trending/go?since=weekly",
}
MANDATORY = "all"
API_RETRIES = 2


@dataclass
class Result:
    ok: bool
    path: Path | None = None
    reason: str = ""
    summary: str = ""


def run(fetch, client, root, today, now_iso, sleep=None) -> Result:
    root = Path(root)
    parsed, status, degradations = {}, {}, []

    for board, url in BOARDS.items():
        try:
            parsed[board] = parse_trending(fetch(url))
            status[board] = "ok"
        except (OSError, ParseError) as e:
            if board == MANDATORY:
                return Result(ok=False, reason=f"board '{board}' failed: {e}")
            status[board] = "failed"
            degradations.append(f"board '{board}' failed: {e}")

    for board, repos in parsed.items():
        missing = [r.full_name for r in repos if r.stars_this_week is None]
        if missing:
            degradations.append(f"board '{board}': stars this week missing for {', '.join(missing)}")

    repos = enrich(merge(parsed), client, retries=API_RETRIES, sleep=sleep)
    unknown = [e.full_name for e in repos if e.total_stars is None]
    if unknown:
        degradations.append(f"REST API lookup failed for {', '.join(unknown)}")

    week = week_id(today)
    base_week, base_repos, skipped = find_baseline(root / "data", week)
    if skipped:
        degradations.append(f"unreadable earlier data files skipped: {', '.join(skipped)}")
    diff = apply_diff(repos, base_repos)

    meta = {
        "boards": status,
        "degradations": degradations,
        "baseline_week": base_week,
        "baseline_skipped": skipped,
    }
    path = write_snapshot(root, today, repos, now_iso, meta=meta, diff=diff)
    counts = ", ".join(f"{b}={len(r)}" for b, r in parsed.items())
    summary = (
        f"wrote {path} ({len(repos)} repos; {counts}); "
        f"baseline={base_week or 'none (first period)'}; "
        f"new={len(diff['new'])} continuing={len(diff['continuing'])} dropped={len(diff['dropped'])}; "
        f"degradations={len(degradations)}"
    )
    return Result(ok=True, path=path, summary=summary)
