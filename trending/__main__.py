"""Entry point for GitHub Actions: fetch the weekly Trending page and write data/YYYY-Www.json.

Usage: python -m trending [--html FILE] [--root DIR]
Exit code 1 (and no data file written) when the page cannot be parsed — spec v1.1 §6.1.
"""
import argparse
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from trending.parser import ParseError, parse_trending
from trending.snapshot import write_snapshot

URL = "https://github.com/trending?since=weekly"
TZ = ZoneInfo("Asia/Taipei")


def fetch(url: str = URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "github-trend-radar"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, help="parse this file instead of fetching")
    ap.add_argument("--root", type=Path, default=Path("."))
    args = ap.parse_args(argv)

    html = args.html.read_text(encoding="utf-8") if args.html else fetch()
    try:
        repos = parse_trending(html)
    except ParseError as e:
        print(f"Trending parse failed: {e}", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    path = write_snapshot(args.root, now.astimezone(TZ).date(), repos, now.isoformat(timespec="seconds"))
    print(f"wrote {path} ({len(repos)} repos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
