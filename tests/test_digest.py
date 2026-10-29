from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from trending_digest.cli import generate
from trending_digest.core import (
    fetch_html,
    load_config,
    make_snapshot,
    parse_count,
    parse_trending,
    previous_snapshot,
    trending_url,
)
from trending_digest.render import movement, render_digest, update_readme

FIXTURE = Path(__file__).parent / "fixtures/trending.html"
CONFIG = {"language": "", "spoken_language": "", "top_n": 1, "timezone": "Asia/Shanghai"}


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.repos = parse_trending(FIXTURE.read_text(encoding="utf-8"))
        self.snapshot = make_snapshot(self.repos, CONFIG, datetime(2026, 10, 28, 18, tzinfo=UTC))

    def test_parse_order_counts_missing_and_duplicates(self):
        self.assertEqual([r["name"] for r in self.repos], ["demo/agent-kit", "demo/database"])
        self.assertEqual(self.repos[0]["stars"], 12345)
        self.assertEqual(self.repos[0]["stars_today"], 1234)
        self.assertEqual(self.repos[1]["stars"], 1200)
        self.assertEqual(self.repos[1]["stars_today"], 1)
        self.assertIsNone(self.repos[1]["forks"])
        self.assertIsNone(self.repos[1]["language"])
        self.assertIsNone(parse_count("missing"))

    def test_empty_or_blocked_page_fails(self):
        for html in ("", "<html>Please sign in</html>", "<article class='Box-row'></article>"):
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_trending(html)

    def test_timezone_and_language_url(self):
        self.assertEqual(self.snapshot["date"], "2026-10-29")
        self.assertIn(
            "/c%2B%2B?since=daily&spoken_language_code=zh",
            trending_url({**CONFIG, "language": "c++", "spoken_language": "zh"}),
        )

    def test_rank_changes_only_against_snapshot(self):
        previous = {"repositories": [{"name": "demo/agent-kit", "rank": 3}]}
        self.assertEqual(movement(self.repos[0], previous), "↑ 2")
        self.assertEqual(movement(self.repos[1], previous), "新入当前采集榜单")
        self.assertEqual(movement(self.repos[0], None), "首次采集，无可比快照")

    def test_markdown_escaping_and_full_table(self):
        digest = render_digest(self.snapshot, None)
        self.assertIn("### 1.", digest)
        self.assertNotIn("### 2.", digest)
        self.assertIn("[demo/database]", digest)
        snapshot = {**self.snapshot, "top_n": 2}
        self.assertIn(r"pipes \| and \[links\]", render_digest(snapshot, None))

    def test_readme_preserves_manual_content(self):
        readme = "Intro\n<!-- digest:start -->\nold\n<!-- digest:end -->\nKeep me\n"
        updated = update_readme(readme, self.snapshot)
        self.assertTrue(updated.startswith("Intro\n"))
        self.assertTrue(updated.endswith("\nKeep me\n"))
        self.assertNotIn("\nold\n", updated)
        self.assertEqual(update_readme(updated, self.snapshot), updated)
        with self.assertRaises(ValueError):
            update_readme("No markers", self.snapshot)

    def test_previous_snapshot_excludes_today_future_and_other_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "data/2026/10"
            directory.mkdir(parents=True)
            for day in ("2026-10-25", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"):
                source = "other" if day == "2026-10-28" else self.snapshot["source_url"]
                (directory / f"{day}.json").write_text(
                    json.dumps({"date": day, "source_url": source})
                )
            previous = previous_snapshot(root, "2026-10-29", self.snapshot["source_url"])
            self.assertEqual(previous["date"], "2026-10-27")

    def test_generation_rerun_and_failure_preserve_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text(
                "<!-- digest:start -->\n<!-- digest:end -->", encoding="utf-8"
            )
            (root / "config.json").write_text(json.dumps(CONFIG))
            first = generate(root, root / "config.json", FIXTURE)
            second = generate(root, root / "config.json", FIXTURE)
            self.assertEqual(first["date"], second["date"])
            self.assertEqual(len(list((root / "data").rglob("*.json"))), 1)
            latest = (root / "latest.md").read_bytes()
            with patch("trending_digest.cli.fetch_html", return_value="Access denied"):
                with self.assertRaises(ValueError):
                    generate(root, root / "config.json")
            self.assertEqual((root / "latest.md").read_bytes(), latest)

    def test_retry_transient_http_error(self):
        error = HTTPError("https://github.com/trending", 503, "Unavailable", {}, None)
        with patch("trending_digest.core.urlopen", side_effect=[error, error, error]) as opened:
            with patch("trending_digest.core.time.sleep") as sleep:
                with self.assertRaises(HTTPError):
                    fetch_html("https://github.com/trending")
                self.assertEqual(opened.call_count, 3)
                self.assertEqual(sleep.call_count, 2)

    def test_configuration_rejects_invalid_top_n(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            for top_n in (0, 26, True, "10"):
                path.write_text(json.dumps({**CONFIG, "top_n": top_n}))
                with self.subTest(top_n=top_n), self.assertRaises(ValueError):
                    load_config(path)


if __name__ == "__main__":
    unittest.main()
