from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from trending_digest.config import load_config, validate_config
from trending_digest.matching import selected_repositories
from trending_digest.service import (
    list_profiles,
    load_profile,
    run_generation,
    save_configuration,
)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        for name in ("README.md", "docs/README.zh-CN.md"):
            (self.root / name).write_text("<!-- digest:start -->\n<!-- digest:end -->")
        self.sha = "a" * 40
        self.snapshot = {
            "date": "2026-10-29",
            "fetched_at": "2026-10-29T09:17:00+08:00",
            "source_url": "https://github.com/trending?since=daily",
            "top_n": 1,
            "default_language": "en",
            "languages": ["en", "zh-CN"],
            "schema_version": 2,
            "repositories": [
                {
                    "name": "example/tool",
                    "url": "https://github.com/example/tool",
                    "language": "Python",
                    "stars": 100,
                    "stars_today": 10,
                    "readme": {
                        "sha": self.sha,
                        "url": "https://github.com/example/tool/blob/main/README.md",
                    },
                }
            ],
        }
        path = self.root / "output/data/2026/10/2026-10-29.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(self.snapshot))
        (self.root / "summaries.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "projects": {
                        "example/tool": {
                            "readme_sha": self.sha,
                            "en": {
                                "purpose": "Indexes documents.",
                                "highlights": ["Local search."],
                            },
                            "zh-CN": {
                                "purpose": "为文档建立索引。",
                                "highlights": ["支持本地搜索。"],
                            },
                        }
                    },
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

    def test_legacy_config_migrates_to_one_active_language(self):
        config = validate_config({"default_language": "zh-CN", "languages": ["en", "zh-CN"]})
        self.assertEqual(config["active_language"], "zh-CN")
        self.assertNotIn("languages", config)
        self.assertNotIn("default_language", config)

    def test_invalid_form_never_replaces_saved_configuration(self):
        save_configuration(self.root, {"active_language": "en"})
        original = (self.root / "conf.yaml").read_bytes()
        with self.assertRaises(ValueError):
            save_configuration(self.root, {"active_language": "unsupported"})
        self.assertEqual((self.root / "conf.yaml").read_bytes(), original)

    def test_named_configurations_persist_load_and_overwrite_independently(self):
        config = validate_config(
            {
                "work_requirements": {
                    "enabled": True,
                    "description": "游戏开发",
                    "keywords": ["Unreal", "性能"],
                }
            }
        )
        save_configuration(self.root, config, profile_name="游戏开发")
        save_configuration(self.root, {"top_n": 2}, profile_name="Backend tools")
        self.assertEqual(list_profiles(self.root), ["Backend tools", "游戏开发"])
        before = (self.root / "conf.yaml").read_bytes()
        self.assertEqual(load_profile(self.root, "游戏开发"), config)
        self.assertEqual((self.root / "conf.yaml").read_bytes(), before)
        config["top_n"] = 3
        save_configuration(self.root, config, profile_name="游戏开发")
        self.assertEqual(load_profile(self.root, "游戏开发")["top_n"], 3)
        self.assertEqual(load_profile(self.root, "Backend tools")["top_n"], 2)
        self.assertEqual(load_config(self.root / "conf.yaml"), config)

    def test_invalid_profile_name_or_config_preserves_saved_files(self):
        save_configuration(self.root, {}, profile_name="valid")
        before = (self.root / "conf.yaml").read_bytes()
        named_before = (self.root / "configs/valid.yaml").read_bytes()
        for name in ("", "../escape", "a/b", "a\\b", "C:drive", "CON", "nul", "LPT1", " x "):
            with self.subTest(name=name), self.assertRaises(ValueError):
                save_configuration(self.root, {"top_n": 2}, profile_name=name)
            self.assertEqual((self.root / "conf.yaml").read_bytes(), before)
        with self.assertRaises(ValueError):
            save_configuration(self.root, {"top_n": 0}, profile_name="valid")
        self.assertEqual((self.root / "configs/valid.yaml").read_bytes(), named_before)
        with self.assertRaises(FileNotFoundError):
            load_profile(self.root, "missing")

    def test_legacy_cached_summary_evidence_survives_locale_switch(self):
        english = run_generation(self.root, {"active_language": "en"}, cached=True)
        config = {
            "active_language": "zh-CN",
            "summary": {"mode": "extractive"},
            "work_requirements": {"enabled": True, "keywords": ["documents"]},
        }
        cached = run_generation(self.root, config, cached=True)
        self.assertEqual(len(selected_repositories(cached)), 1)
        self.assertEqual(cached["fetched_at"], english["fetched_at"])

    def test_cached_generation_only_publishes_selected_language(self):
        english = run_generation(self.root, {"active_language": "en"}, cached=True)
        self.assertEqual(list(english["repositories"][0]["summary"]["locales"]), ["en"])
        english_path = self.root / "output/reports/2026/10/2026-10-29.html"
        original = english_path.read_bytes()
        result = run_generation(self.root, {"active_language": "zh-CN"}, cached=True)
        self.assertEqual(result["active_language"], "zh-CN")
        self.assertNotIn("default_language", result)
        self.assertNotIn("languages", result)
        self.assertEqual(list(result["repositories"][0]["summary"]["locales"]), ["zh-CN"])
        self.assertEqual(original, english_path.read_bytes())
        self.assertIn(
            'lang="zh-CN"', (self.root / "output/reports/index.html").read_text(encoding="utf-8")
        )
        self.assertEqual(load_config(self.root / "conf.yaml")["active_language"], "zh-CN")


if __name__ == "__main__":
    unittest.main()
