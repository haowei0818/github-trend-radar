"""Fill total stars, topics and creation date from the GitHub REST API.

The API client is injected (`client(full_name) -> dict`), so tests need no
network or token. A failed lookup leaves that repo's fields as None (unknown);
it never stops the run. Recording the degradation belongs to T6.
"""
import json
import os
import urllib.request

from trending.merge import Entry


def enrich(entries: list[Entry], client, retries: int = 0, sleep=None) -> list[Entry]:
    for e in entries:
        data = _with_retry(lambda: client(e.full_name), retries, sleep)
        if data is None:
            continue
        e.total_stars = data.get("stargazers_count")
        e.topics = list(data.get("topics") or [])
        created = data.get("created_at")
        e.created_at = created[:10] if created else None
    return entries


def _with_retry(call, retries, sleep):
    for attempt in range(retries + 1):
        try:
            return call()
        except Exception:
            if attempt < retries and sleep:
                sleep(2 ** attempt)
    return None


def github_client(token: str | None = None):
    token = token if token is not None else os.environ.get("GITHUB_TOKEN")

    def get_repo(full_name: str) -> dict:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{full_name}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "github-trend-radar",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)

    return get_repo
