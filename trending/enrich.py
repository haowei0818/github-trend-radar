"""Fill total stars, topics and creation date from the GitHub REST API.

The API client is injected (`client(full_name) -> dict`), so tests need no
network or token. A failed lookup leaves that repo's fields as None (unknown);
it never stops the run. Recording the degradation belongs to T6.
"""
import json
import os
import urllib.request

from trending.merge import Entry


def enrich(entries: list[Entry], client) -> list[Entry]:
    for e in entries:
        try:
            data = client(e.full_name)
        except Exception:
            continue
        e.total_stars = data.get("stargazers_count")
        e.topics = list(data.get("topics") or [])
        created = data.get("created_at")
        e.created_at = created[:10] if created else None
    return entries


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
