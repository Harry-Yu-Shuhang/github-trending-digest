from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from trending_digest.cli import generate
from trending_digest.config import validate_config
from trending_digest.matching import match_repository, selected_repositories
from trending_digest.service import run_generation, save_configuration

PAGE = Path(__file__).parent / "fixtures/trending.html"


class WorkRequirementTests(unittest.TestCase):
    def test_invalid_rules_are_rejected_and_keywords_are_deduplicated(self):
        for rules in (
            {"enabled": "true"},
            {"description": []},
            {"keywords": "Python"},
            {"keywords": [""]},
            {"exclude_keywords": [None]},
            {"min_matches": True},
            {"enabled": True},
            {"enabled": True, "keywords": ["AI", "ai"], "min_matches": 2},
            {"unknown": 1},
        ):
            with self.subTest(rules=rules), self.assertRaises(ValueError):
                validate_config({"work_requirements": rules})
        config = validate_config({"work_requirements": {"keywords": [" Python ", "python"]}})
        self.assertEqual(config["work_requirements"]["keywords"], ["Python"])

    def test_case_boundaries_chinese_and_exclusions(self):
        rules = validate_config(
            {
                "work_requirements": {
                    "enabled": True,
                    "keywords": ["AI", "C++", "性能分析"],
                    "exclude_keywords": ["cloud only"],
                    "min_matches": 2,
                }
            }
        )["work_requirements"]
        repo = {"name": "demo/rail", "description": "C++ 性能分析工具"}
        result = match_repository(repo, rules)
        self.assertTrue(result["useful"])
        self.assertEqual(result["matched_keywords"], ["C++", "性能分析"])
        repo["description"] += " — CLOUD ONLY"
        self.assertFalse(match_repository(repo, rules)["useful"])
        self.assertEqual(match_repository(repo, rules)["excluded_keywords"], ["cloud only"])

    def test_fresh_and_cached_filters_keep_all_candidates_and_apply_top_n_after_matching(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            for name in ("README.md", "docs/README.zh-CN.md"):
                (root / name).write_text("<!-- digest:start -->\n<!-- digest:end -->")
            config = validate_config(
                {
                    "top_n": 1,
                    "summary": {"mode": "extractive"},
                    "work_requirements": {
                        "enabled": True,
                        "description": "Find <offline> tools for my work",
                        "keywords": ["needleword"],
                    },
                }
            )
            save_configuration(root, config)

            def readme(repo, timeout):
                term = "haystackword" if repo["name"].endswith("agent-kit") else "needleword"
                return {
                    "status": "ok",
                    "sha": "a" * 40,
                    "url": repo["url"] + "#readme",
                    # The keyword is outside the 350-character summary excerpt.
                    "text": "# Tool\n\n"
                    + "A local development toolkit with useful features. " * 20
                    + "\n\n"
                    + term,
                }

            with patch("trending_digest.readmes.fetch_readme", side_effect=readme) as fetch:
                snapshot = generate(root, root / "conf.yaml", PAGE)
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(len(snapshot["repositories"]), 2)
            self.assertEqual(selected_repositories(snapshot)[0]["name"], "demo/database")
            page = BeautifulSoup(
                (root / "output/reports/index.html").read_text("utf-8"), "html.parser"
            )
            self.assertEqual(len(page.select("article.project")), 1)
            self.assertIn("needleword", page.select_one(".work-match").get_text())
            self.assertIsNone(page.select_one("offline"))
            self.assertIn("<offline>", page.select_one(".work-requirements").get_text())
            self.assertIn("demo/database", (root / "output/latest.md").read_text("utf-8"))
            self.assertNotIn("demo/agent-kit", (root / "README.md").read_text("utf-8"))

            # A different requirement can recover a previously unselected candidate offline.
            config["work_requirements"]["keywords"] = ["haystackword"]
            with patch(
                "trending_digest.readmes.fetch_readme", side_effect=AssertionError("network")
            ):
                cached = run_generation(root, config, cached=True)
            self.assertEqual(selected_repositories(cached)[0]["name"], "demo/agent-kit")
            config["work_requirements"]["keywords"] = ["needleword"]
            cached = run_generation(root, config, cached=True)
            self.assertEqual(selected_repositories(cached)[0]["name"], "demo/database")

            config["work_requirements"]["exclude_keywords"] = ["needleword"]
            cached = run_generation(root, config, cached=True)
            self.assertEqual(selected_repositories(cached), [])
            self.assertIn("No repositories matched", (root / "output/latest.md").read_text("utf-8"))
            page = BeautifulSoup(
                (root / "output/reports/index.html").read_text("utf-8"), "html.parser"
            )
            self.assertEqual(len(page.select("article.project")), 0)
            self.assertIn("No repositories matched", page.get_text())

            config["work_requirements"]["enabled"] = False
            cached = run_generation(root, config, cached=True)
            self.assertEqual(selected_repositories(cached)[0]["name"], "demo/agent-kit")
            self.assertTrue(all("work_match" not in repo for repo in cached["repositories"]))


if __name__ == "__main__":
    unittest.main()
