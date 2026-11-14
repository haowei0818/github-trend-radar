import unittest

from trending.enrich import enrich
from trending.merge import Entry


def entry(name):
    return Entry(name, "d", "Python", 10, ["all"])


# Shape of GET /repos/{owner}/{repo} (only the fields we read, plus noise).
API = {
    "acme/widget": {
        "full_name": "acme/widget",
        "stargazers_count": 12345,
        "topics": ["llm", "rag"],
        "created_at": "2024-03-01T08:00:00Z",
        "forks_count": 99,
    },
    "acme/bare": {"full_name": "acme/bare", "stargazers_count": 7, "created_at": "2025-01-02T00:00:00Z"},
}


class FakeClient:
    def __init__(self, data, fail=()):
        self.data, self.fail, self.calls = data, set(fail), []

    def __call__(self, full_name):
        self.calls.append(full_name)
        if full_name in self.fail:
            raise OSError("boom")
        return self.data[full_name]


class EnrichTest(unittest.TestCase):
    def test_fills_total_stars_topics_and_created_date(self):
        out = enrich([entry("acme/widget")], FakeClient(API))
        e = out[0]
        self.assertEqual(e.total_stars, 12345)
        self.assertEqual(e.topics, ["llm", "rag"])
        self.assertEqual(e.created_at, "2024-03-01")

    def test_trending_fields_are_untouched(self):
        e = enrich([entry("acme/widget")], FakeClient(API))[0]
        self.assertEqual((e.full_name, e.stars_this_week, e.boards), ("acme/widget", 10, ["all"]))

    def test_missing_topics_key_becomes_empty_list(self):
        self.assertEqual(enrich([entry("acme/bare")], FakeClient(API))[0].topics, [])

    def test_one_failed_lookup_leaves_only_that_repo_unknown(self):
        client = FakeClient(API, fail={"acme/widget"})
        out = enrich([entry("acme/widget"), entry("acme/bare")], client)
        self.assertEqual((out[0].total_stars, out[0].topics, out[0].created_at), (None, None, None))
        self.assertEqual(out[1].total_stars, 7)

    def test_calls_api_once_per_repo_in_order(self):
        client = FakeClient(API)
        enrich([entry("acme/widget"), entry("acme/bare")], client)
        self.assertEqual(client.calls, ["acme/widget", "acme/bare"])


if __name__ == "__main__":
    unittest.main()
