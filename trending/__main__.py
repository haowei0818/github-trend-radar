"""Entry point for GitHub Actions. See trending/pipeline.py for behaviour.

Usage: python -m trending [--root DIR]
Exit code 1 (no data file written) when the all-language board fails.
"""
import argparse
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from trending.enrich import github_client
from trending.pipeline import run

TZ = ZoneInfo("Asia/Taipei")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "github-trend-radar"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    args = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    result = run(fetch, github_client(), args.root, now.astimezone(TZ).date(),
                 now.isoformat(timespec="seconds"), sleep=time.sleep)
    if not result.ok:
        print(f"FAILED: {result.reason}", file=sys.stderr)
        return 1
    print(result.summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
