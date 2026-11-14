"""Weekly data file: data/YYYY-Www.json (ISO week), the cross-week source of truth."""
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from trending.parser import Repo


def week_id(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def data_path(d: date) -> Path:
    return Path("data") / f"{week_id(d)}.json"


def write_snapshot(root: Path, d: date, repos: list, generated_at: str, meta: dict | None = None, diff: dict | None = None) -> Path:
    path = Path(root) / data_path(d)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {"week": week_id(d), "generated_at": generated_at, **(meta or {})},
        "repos": [asdict(r) for r in repos],
    }
    if diff is not None:
        payload["diff"] = diff
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)  # atomic overwrite on rerun
    return path
