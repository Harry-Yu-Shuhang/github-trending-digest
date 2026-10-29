from __future__ import annotations

import base64
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import yaml

from trending_digest.cli import generate
from trending_digest.config import load_config
from trending_digest.core import (
    fetch_html,
    make_snapshot,
    parse_count,
    parse_trending,
    trending_url,
)
from trending_digest.readmes import (
    clean_readme,
    enrich_repositories,
    extract_passages,
    fetch_readme,
    load_curated,
)
from trending_digest.render import archive_index, render_digest, update_readme

FIXTURES = Path(__file__).parent / "fixtures"
PAGE = FIXTURES / "trending.html"
README = (FIXTURES / "project-readme.md").read_text(encoding="utf-8")
SHA = "a" * 40


def write_config(root: Path, **overrides) -> dict:
    path = root / "conf.yaml"
    path.write_text(yaml.safe_dump(overrides), encoding="utf-8")
    return load_config(path)


def readme_result(*args) -> dict:
    return {
        "sha": SHA,
        "url": "https://github.com/demo/agent-kit/blob/main/README.md",
        "path": "README.md",
        "status": "ok",
        "text": README,
    }


def curated_entry() -> dict:
    return {
        "readme_sha": SHA,
        "en": {
            "purpose": "Indexes local documents for search.",
            "highlights": ["Preserves source references.", "Rebuilds incrementally."],
        },
        "zh-CN": {
            "purpose": "将本地文档建立索引以便搜索。",
            "highlights": ["保留来源引用。", "支持增量构建。"],
        },
    }


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        self.config = write_config(self.root, top_n=1)
        self.repos = parse_trending(PAGE.read_text(encoding="utf-8"))
        with patch("trending_digest.readmes.fetch_readme", side_effect=readme_result):
            self.enriched = enrich_repositories(self.repos, self.root, self.config)
        self.snapshot = make_snapshot(
            self.enriched, self.config, datetime(2026, 10, 28, 18, tzinfo=UTC)
        )

    def test_parse_order_counts_missing_and_duplicates(self):
        self.assertEqual([r["name"] for r in self.repos], ["demo/agent-kit", "demo/database"])
        self.assertEqual(self.repos[0]["stars"], 12345)
        self.assertEqual(self.repos[0]["stars_today"], 1234)
        self.assertEqual(self.repos[1]["stars"], 1200)
        self.assertEqual(self.repos[1]["stars_today"], 1)
        self.assertIsNone(self.repos[1]["forks"])
        self.assertIsNone(parse_count("missing"))

    def test_repository_yaml_configuration_and_curated_notes_are_valid(self):
        root = Path(__file__).resolve().parents[2]
        config = load_config(root / "conf.yaml")
        self.assertIn(config["active_language"], {"en", "zh-CN"})
        self.assertNotIn("default_language", config)
        self.assertNotIn("languages", config)
        self.assertTrue(
            load_curated(root / config["summary"]["curated_file"], [config["active_language"]])
        )

    def test_empty_or_blocked_page_fails(self):
        for page in ("", "<html>Please sign in</html>", "<article class='Box-row'></article>"):
            with self.subTest(page=page), self.assertRaises(ValueError):
                parse_trending(page)

    def test_timezone_and_language_filter(self):
        self.assertEqual(self.snapshot["date"], "2026-10-29")
        self.assertIn(
            "/c%2B%2B?since=daily&spoken_language_code=zh",
            trending_url({**self.config, "programming_language": "c++", "spoken_language": "zh"}),
        )

    def test_bilingual_reports_have_project_cards_without_leaderboard(self):
        english = render_digest(self.snapshot)
        config = {**self.config, "active_language": "zh-CN"}
        with patch("trending_digest.readmes.fetch_readme", side_effect=readme_result):
            repos = enrich_repositories(self.repos, self.root, config)
        chinese = render_digest(
            make_snapshot(repos, config, datetime(2026, 10, 28, 18, tzinfo=UTC))
        )
        self.assertTrue(english.startswith("# GitHub Tech Brief"))
        self.assertTrue(chinese.startswith("# GitHub 技术快报"))
        self.assertIn("What it does", english)
        self.assertIn("这是做什么的", chinese)
        self.assertIn("## [demo/agent-kit]", english)
        self.assertNotIn("demo/database", english)
        self.assertNotIn("| ---", english)
        self.assertNotIn("完整榜单", chinese)
        self.assertNotIn("2026-10-29.zh-CN.md", english)
        self.assertNotIn("(2026-10-29.md)", chinese)

    def test_extraction_uses_readme_not_trending_description(self):
        summary = self.enriched[0]["summary"]
        self.assertEqual(summary["status"], "extractive")
        self.assertIn("offline document toolkit", summary["locales"]["en"]["purpose"])
        self.assertNotIn("AI agent toolkit", summary["locales"]["en"]["purpose"])
        self.assertIn("summary pending", render_digest(self.snapshot))

    def test_cleaner_removes_code_hidden_text_and_scripts(self):
        cleaned = clean_readme(README)
        self.assertNotIn("do not execute", cleaned)
        self.assertNotIn("hidden instructions", cleaned)
        self.assertNotIn("script content", cleaned)
        purpose, highlights = extract_passages(README, 3, 350)
        self.assertIn("document toolkit", purpose)
        self.assertEqual(len(highlights), 2)
        self.assertFalse(any("installation" in text.lower() for text in [purpose, *highlights]))

    def test_curated_summary_requires_matching_sha_and_both_locales(self):
        path = self.root / "summaries.yaml"
        path.write_text(
            yaml.safe_dump({"schema_version": 1, "projects": {"demo/agent-kit": curated_entry()}}),
            encoding="utf-8",
        )
        with patch("trending_digest.readmes.fetch_readme", side_effect=readme_result):
            enriched = enrich_repositories(self.repos, self.root, self.config)
        summary = enriched[0]["summary"]
        self.assertEqual(summary["status"], "curated")
        self.assertEqual(list(summary["locales"]), ["en"])
        changed = {**readme_result(), "sha": "b" * 40}
        with patch("trending_digest.readmes.fetch_readme", return_value=changed):
            self.assertEqual(
                enrich_repositories(self.repos, self.root, self.config)[0]["summary"]["status"],
                "extractive",
            )
        entry = curated_entry()
        del entry["zh-CN"]
        path.write_text(
            yaml.safe_dump({"schema_version": 1, "projects": {"demo/agent-kit": entry}}),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            load_curated(path, ["en", "zh-CN"])

    def test_missing_readme_does_not_invent_a_description(self):
        missing = {"status": "missing", "url": self.repos[0]["url"] + "#readme"}
        with patch("trending_digest.readmes.fetch_readme", return_value=missing):
            result = enrich_repositories(self.repos, self.root, self.config)[0]
        self.assertEqual(result["summary"]["status"], "unavailable")
        self.assertEqual(result["summary"]["locales"]["en"]["purpose"], "")

    def test_fetch_readme_decodes_actual_file_and_handles_404(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {
                "sha": SHA,
                "html_url": "https://github.com/demo/repo/blob/main/README.rst",
                "path": "README.rst",
                "encoding": "base64",
                "content": base64.b64encode(README.encode()).decode(),
            }
        ).encode()
        with patch("trending_digest.readmes.urlopen", return_value=response):
            result = fetch_readme(self.repos[0], 30)
        self.assertEqual(result["text"], README)
        error = HTTPError("https://api.github.com/", 404, "Missing", {}, None)
        with patch("trending_digest.readmes.urlopen", side_effect=error):
            self.assertEqual(fetch_readme(self.repos[0], 30)["status"], "missing")

    def test_readme_manual_content_and_localized_preview(self):
        readme = "Intro\n<!-- digest:start -->\nold\n<!-- digest:end -->\nKeep me\n"
        updated = update_readme(readme, self.snapshot)
        self.assertTrue(updated.startswith("Intro\n"))
        self.assertTrue(updated.endswith("\nKeep me\n"))
        self.assertNotIn("\nold\n", updated)
        self.assertEqual(update_readme(updated, self.snapshot), updated)
        self.assertIn("2026-10-29.md", update_readme(readme, self.snapshot))
        with self.assertRaises(ValueError):
            update_readme("No markers", self.snapshot)

    def test_generation_only_writes_active_language_and_preserves_other_editions(self):
        user_readme = self.root / "README.md"
        user_readme.write_text(
            "User-maintained quick start\n<!-- digest:start -->\n<!-- digest:end -->",
            encoding="utf-8",
        )
        for name in ("docs/README.zh-CN.md",):
            (self.root / name).write_text("<!-- digest:start -->\n<!-- digest:end -->")
        with patch("trending_digest.readmes.fetch_readme", side_effect=readme_result):
            first = generate(self.root, self.root / "conf.yaml", PAGE)
            generate(self.root, self.root / "conf.yaml", PAGE)
        day = first["date"]
        self.assertTrue(
            user_readme.read_text(encoding="utf-8").startswith("User-maintained quick start\n")
        )
        for name in ("reports", "daily", "data", "latest.md", "README.zh-CN.md"):
            self.assertFalse((self.root / name).exists(), name)
        self.assertIn(
            f"output/daily/{day[:4]}/{day[5:7]}/{day}.md",
            (self.root / "README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(len(list((self.root / "output/data").rglob("*.json"))), 1)
        self.assertFalse((self.root / "output/latest.zh-CN.md").exists())
        self.assertTrue((self.root / "output/reports/index.html").exists())
        self.assertFalse((self.root / "output/reports/index.zh-CN.html").exists())
        self.assertTrue((self.root / f"output/reports/{day[:4]}/{day[5:7]}/{day}.html").exists())
        english_readme = (self.root / "README.md").read_bytes()
        english_issue = self.root / f"output/daily/{day[:4]}/{day[5:7]}/{day}.md"
        english_content = english_issue.read_bytes()
        write_config(self.root, active_language="zh-CN", top_n=1)
        with patch("trending_digest.readmes.fetch_readme", side_effect=readme_result):
            result = generate(self.root, self.root / "conf.yaml", PAGE)
        self.assertEqual(result["active_language"], "zh-CN")
        self.assertEqual(list(result["repositories"][0]["summary"]["locales"]), ["zh-CN"])
        self.assertEqual(english_issue.read_bytes(), english_content)
        self.assertEqual((self.root / "README.md").read_bytes(), english_readme)
        self.assertIn(
            'lang="zh-CN"', (self.root / "output/reports/index.html").read_text(encoding="utf-8")
        )
        self.assertIn(
            f"{day}.zh-CN.html",
            (self.root / "output/reports/archive.html").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f"{day}.zh-CN.md", (self.root / "output/daily/README.md").read_text(encoding="utf-8")
        )
        latest = (self.root / "output/latest.md").read_bytes()
        with patch("trending_digest.cli.fetch_html", return_value="Access denied"):
            with self.assertRaises(ValueError):
                generate(self.root, self.root / "conf.yaml")
        self.assertEqual((self.root / "output/latest.md").read_bytes(), latest)
        (self.root / "docs/README.zh-CN.md").write_text("Missing markers")
        with patch("trending_digest.readmes.fetch_readme", side_effect=readme_result):
            with self.assertRaises(ValueError):
                generate(self.root, self.root / "conf.yaml", PAGE)
        self.assertEqual((self.root / "output/latest.md").read_bytes(), latest)

    def test_archive_does_not_link_missing_language_files(self):
        (self.root / "output/data/2026/10").mkdir(parents=True)
        (self.root / "output/data/2026/10/2026-10-28.json").write_text("{}")
        index = archive_index(self.root / "output", "zh-CN")
        self.assertNotIn("2026-10-28", index)

    def test_retry_transient_trending_error(self):
        error = HTTPError("https://github.com/trending", 503, "Unavailable", {}, None)
        with patch("trending_digest.core.urlopen", side_effect=[error, error, error]) as opened:
            with patch("trending_digest.core.time.sleep") as sleep:
                with self.assertRaises(HTTPError):
                    fetch_html("https://github.com/trending")
                self.assertEqual(opened.call_count, 3)
                self.assertEqual(sleep.call_count, 2)

    def test_yaml_config_rejects_invalid_values_and_unknown_keys(self):
        for override in (
            {"top_n": 0},
            {"top_n": True},
            {"active_language": "fr"},
            {"active_language": ["en", "zh-CN"]},
            {"unknown": 1},
            {"summary": {"mode": "unimplemented"}},
            {"readme": {"workers": 0}},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                write_config(self.root, **override)


if __name__ == "__main__":
    unittest.main()
