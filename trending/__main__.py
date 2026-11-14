"""Entry point for GitHub Actions: fetch weekly Trending boards and write data/YYYY-Www.json.

Boards: all languages, then Python, TypeScript, Go (spec v1.1 §3.1). They are merged
(§5.3) and enriched from the REST API. Exit code 1 and no data file when a board
cannot be parsed (per-board degradation is T6).

Usage: python -m trending [--html FILE] [--root DIR]
  --html parses one local file as the all-language board only (no network).
"""
import argparse
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from trending.diff import apply_diff, find_baseline
from trending.enrich import enrich, github_client
from trending.merge import merge
from trending.parser import ParseError, parse_trending
from trending.snapshot import week_id, write_snapshot

BOARDS = {
    "all": "https://github.com/trending?since=weekly",
    "python": "https://github.com/trending/python?since=weekly",
    "typescript": "https://github.com/trending/typescript?since=weekly",
    "go": "https://github.com/trending/go?since=weekly",
}
TZ = ZoneInfo("Asia/Taipei")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "github-trend-radar"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, help="parse this file instead of fetching")
    ap.add_argument("--root", type=Path, default=Path("."))
    args = ap.parse_args(argv)

    pages = {"all": args.html.read_text(encoding="utf-8")} if args.html else {b: fetch(u) for b, u in BOARDS.items()}
    try:
        parsed = {board: parse_trending(html) for board, html in pages.items()}
    except ParseError as e:
        print(f"Trending parse failed: {e}", file=sys.stderr)
        return 1

    repos = merge(parsed)
    if not args.html:
        repos = enrich(repos, github_client())

    now = datetime.now(timezone.utc)
    today = now.astimezone(TZ).date()
    base_week, base_repos, skipped = find_baseline(args.root / "data", week_id(today))
    diff = apply_diff(repos, base_repos)
    meta = {"baseline_week": base_week, "baseline_skipped": skipped}
    path = write_snapshot(args.root, today, repos, now.isoformat(timespec="seconds"), meta=meta, diff=diff)
    counts = ", ".join(f"{b}={len(r)}" for b, r in parsed.items())
    print(f"wrote {path} ({len(repos)} repos after merge; {counts})")
    print(f"baseline={base_week or 'none (first period)'} skipped={skipped} "
          f"new={len(diff['new'])} continuing={len(diff['continuing'])} dropped={len(diff['dropped'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
