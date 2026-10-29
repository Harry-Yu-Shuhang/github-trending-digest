from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from bs4 import BeautifulSoup

from trending_digest.html_report import html_outputs, render_html


class HtmlReportTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "date": "2026-10-29",
            "fetched_at": "2026-10-29T09:17:00+08:00",
            "source_url": "https://github.com/trending?since=daily",
            "top_n": 1,
            "active_language": "en",
            "repositories": [
                {
                    "name": "example/project",
                    "url": "https://github.com/example/project",
                    "language": "Python",
                    "stars": 1200,
                    "stars_today": 23,
                    "readme": {"url": "https://github.com/example/project/blob/main/README.md"},
                    "summary": {
                        "status": "curated",
                        "locales": {
                            "en": {
                                "purpose": "Indexes local documents.",
                                "highlights": ["Offline search."],
                            },
                            "zh-CN": {
                                "purpose": "为本地文档建立索引。",
                                "highlights": ["支持离线搜索。"],
                            },
                        },
                    },
                }
            ],
        }

    def test_html_is_standalone_localized_and_semantic(self):
        english = BeautifulSoup(render_html(self.snapshot, latest=True), "html.parser")
        chinese = BeautifulSoup(render_html(self.snapshot, "zh-CN", latest=True), "html.parser")
        self.assertEqual(english.html["lang"], "en")
        self.assertEqual(chinese.html["lang"], "zh-CN")
        self.assertIn("Indexes local documents.", english.get_text())
        self.assertIn("为本地文档建立索引。", chinese.get_text())
        self.assertEqual(len(english.select("article.project")), 1)
        self.assertEqual(len(english.select("h1")), 1)
        self.assertIsNone(english.select_one("script[src], link[rel=stylesheet], img[src]"))
        self.assertIsNotNone(english.select_one("style"))
        self.assertNotIn("index.zh-CN.html", [link["href"] for link in english.select("a[href]")])
        self.assertEqual(len(english.select(".locale-switch a")), 1)
        self.assertIn(
            "../../archive.html",
            [
                link["href"]
                for link in BeautifulSoup(render_html(self.snapshot), "html.parser").select(
                    "a[href]"
                )
            ],
        )

    def test_source_content_cannot_inject_html_or_script_urls(self):
        malicious = deepcopy(self.snapshot)
        malicious["repositories"][0]["summary"]["locales"]["en"]["purpose"] = (
            '<img src=x onerror="alert(1)">'
        )
        malicious["repositories"][0]["readme"]["url"] = "javascript:alert(1)"
        page = BeautifulSoup(render_html(malicious), "html.parser")
        self.assertIsNone(page.find("img"))
        self.assertIn("<img src=x", page.get_text())
        self.assertEqual(page.select_one(".source-link")["href"], "#")

    def test_current_and_archived_files_have_valid_relative_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = root / "reports/2026/10/2026-10-28.html"
            old.parent.mkdir(parents=True)
            old.write_text("previous issue")
            outputs = html_outputs(root, self.snapshot)
            self.assertEqual(len(outputs), 3)
            for path, text in outputs.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            for path, text in outputs.items():
                page = BeautifulSoup(text, "html.parser")
                ids = [tag["id"] for tag in page.select("[id]")]
                self.assertEqual(len(ids), len(set(ids)))
                for link in page.select("a[href]"):
                    target = link["href"]
                    if target.startswith("https:"):
                        continue
                    if target.startswith("#"):
                        self.assertIn(target[1:], ids)
                    else:
                        self.assertTrue((path.parent / target).exists(), f"{path}: {target}")
            english = outputs[root / "reports/archive.html"]
            self.snapshot["active_language"] = "zh-CN"
            chinese = html_outputs(root, self.snapshot)[root / "reports/archive.html"]
            self.assertIn("2026-10-28.html", english)
            self.assertNotIn("2026-10-28.zh-CN.html", chinese)

    def test_saved_summary_is_not_changed_by_html_rendering(self):
        before = json.dumps(self.snapshot, ensure_ascii=False)
        render_html(self.snapshot)
        self.assertEqual(before, json.dumps(self.snapshot, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
