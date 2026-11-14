"""Week-over-week comparison (spec v1.1 §5.4).

- Baseline: the most recent valid data file strictly before the current week.
  Unreadable files, or files without a repo list, are skipped and reported.
- new        = in this week, not in baseline
- continuing = in both; streak = baseline streak + 1 (a baseline repo without
               a streak field counts as 1)
- dropped    = in baseline, not in this week
Matching is case-insensitive on owner/repo.
"""
import json
import re
from pathlib import Path

_WEEK_FILE = re.compile(r"^\d{4}-W\d{2}\.json$")


def find_baseline(data_dir, current_week: str):
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        return None, None, []
    weeks = sorted(
        (p.stem for p in data_dir.iterdir() if _WEEK_FILE.match(p.name) and p.stem < current_week),
        reverse=True,
    )
    skipped = []
    for week in weeks:
        repos = _load_repos(data_dir / f"{week}.json")
        if repos is not None:
            return week, repos, skipped
        skipped.append(week)
    return None, None, skipped


def _load_repos(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, list) or not all(isinstance(r, dict) and r.get("full_name") for r in repos):
        return None
    return repos


def apply_diff(entries, baseline_repos) -> dict:
    prev = {r["full_name"].lower(): r for r in (baseline_repos or [])}
    current = {e.full_name.lower() for e in entries}
    new, continuing = [], []
    for e in entries:
        b = prev.get(e.full_name.lower())
        if b is None:
            e.streak = 1
            new.append(e.full_name)
        else:
            e.streak = (b.get("streak") or 1) + 1
            continuing.append(e.full_name)
    dropped = [r["full_name"] for r in (baseline_repos or []) if r["full_name"].lower() not in current]
    return {"new": new, "continuing": continuing, "dropped": dropped}
