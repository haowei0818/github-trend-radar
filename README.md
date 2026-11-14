# github-trend-radar

Weekly GitHub Trending snapshot pipeline (GitHub Actions + Python, TDD).

Every Sunday 21:00 (Asia/Taipei) a GitHub Actions workflow fetches the weekly
[GitHub Trending](https://github.com/trending?since=weekly) boards (all languages, Python, TypeScript, Go),
merges and enriches them, parses it and
commits `data/YYYY-Www.json` (ISO week). A separate Claude scheduled task reads
the data file and writes the human-readable trend report.

## Layout

| Path | Role |
|---|---|
| `trending/parser.py` | Trending HTML → `Repo` records; a row without a repo name fails the whole list |
| `trending/merge.py` | Merge boards: case-insensitive dedupe, record every board, max stars this week |
| `trending/enrich.py` | Total stars, topics, created date from the REST API (injected client; failures → unknown) |
| `trending/diff.py` | Week-over-week diff: baseline = latest valid earlier week file; new / continuing (streak) / dropped |
| `trending/snapshot.py` | ISO week id and atomic write of `data/YYYY-Www.json` (reruns overwrite) |
| `trending/pipeline.py` | Whole run behind one function with injected I/O; failure policy (spec §6.1) |
| `trending/__main__.py` | Thin Actions entry point; exit 1 and write nothing when the all-language board fails |
| `tests/` | unittest suite; `fixtures/` holds a real captured Trending page |
| `.github/workflows/weekly.yml` | Weekly schedule + manual trigger; tests must pass before fetching |

## Run locally

```bash
pip install -r requirements.txt
python -m unittest -v
```
