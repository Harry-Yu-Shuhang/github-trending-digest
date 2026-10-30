from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trending_digest.config import validate_config
from trending_digest.service import save_configuration

HAS_GRADIO = importlib.util.find_spec("gradio") is not None


@unittest.skipUnless(HAS_GRADIO, "Install the ui extra to test Gradio")
class UiTests(unittest.TestCase):
    def test_configuration_edits_keep_model_and_source_settings(self):
        from trending_digest.ui import edited_config

        config = validate_config(
            {
                "active_language": "zh-CN",
                "top_n": 7,
                "programming_language": "rust",
                "readme": {"workers": 2},
                "llm": {"model": "configured-model", "api_key_env": "TEST_MODEL_KEY"},
                "work_requirements": {
                    "enabled": True,
                    "description": "本地文档搜索",
                    "keywords": ["search", "搜索"],
                },
            }
        )
        edited = edited_config(config, "en", "New focus")
        self.assertEqual(edited["llm"], config["llm"])
        self.assertEqual(edited["readme"], config["readme"])
        self.assertEqual(edited["programming_language"], "rust")
        self.assertEqual(edited["top_n"], 7)

    def test_ui_builds_with_the_saved_active_language(self):
        from trending_digest.ui import create_ui

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for locale in ("en", "zh-CN"):
                save_configuration(root, {"active_language": locale})
                app = create_ui(root)
                components = app.get_config_file()["components"]
                language = next(
                    component
                    for component in components
                    if component["props"].get("elem_id") == "active-language"
                )
                self.assertEqual(language["props"]["value"], locale)
                self.assertEqual(
                    language["props"]["label"],
                    "Language / 语言",
                )
                self.assertFalse(
                    any(
                        component["type"] in {"number", "slider", "accordion"}
                        for component in components
                    )
                )

    def test_description_edits_keep_yaml_parameters_and_loaded_profile_values(self):
        from trending_digest.ui import create_ui, edited_config

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = save_configuration(
                root,
                {
                    "top_n": 7,
                    "programming_language": "rust",
                    "readme": {"workers": 2},
                },
            )
            updated = edited_config(original, "zh-CN", "游戏性能分析")
            self.assertEqual(original["work_requirements"], {"description": ""})
            self.assertEqual(updated["top_n"], 7)
            self.assertEqual(updated["programming_language"], "rust")
            self.assertEqual(updated["readme"]["workers"], 2)
            app = create_ui(root)
            save = next(fn.fn for fn in app.fns.values() if fn.fn and fn.fn.__name__ == "save_form")
            result = save(original, "zh-CN", "游戏性能分析", "Game tests")
            self.assertEqual(result[0], updated)
            self.assertEqual(result[1], "Game tests")
            from trending_digest.service import load_profile

            self.assertEqual(load_profile(root, "Game tests"), updated)

    def test_empty_work_field_and_report_opens_only_after_successful_generation(self):
        from trending_digest.ui import create_ui, edited_config

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = save_configuration(root, {})
            self.assertEqual(config["work_requirements"]["description"], "")
            app = create_ui(root)
            components = app.get_config_file()["components"]
            self.assertFalse(any(c["props"].get("elem_id") == "report-preview" for c in components))
            callback = next(
                fn.fn for fn in app.fns.values() if fn.fn and fn.fn.__name__ == "generate_form"
            )
            report = root / "output/reports/index.html"
            report.parent.mkdir(parents=True)
            report.write_text("<!doctype html><h1>Report</h1>", encoding="utf-8")
            snapshot = {"date": "2026-10-29", "top_n": 25, "repositories": []}
            with (
                patch("trending_digest.ui.run_generation", return_value=snapshot),
                patch("trending_digest.ui.webbrowser.open_new_tab", return_value=True) as browser,
            ):
                result = callback(config, config["active_language"], "")
                self.assertEqual(result[-1]["kind"], "success")
                browser.assert_called_once_with(report.resolve().as_uri())
            with (
                patch("trending_digest.ui.run_generation", side_effect=ValueError("failed")),
                patch("trending_digest.ui.webbrowser.open_new_tab") as browser,
            ):
                result = callback(config, config["active_language"], "")
                self.assertEqual(result[-1]["kind"], "error")
                self.assertEqual(result[-1]["message"], "failed")
                browser.assert_not_called()
            self.assertEqual(
                edited_config(config, "en", "  Unreal performance  ")["work_requirements"],
                {"description": "Unreal performance"},
            )
            self.assertEqual(
                edited_config(config, "en", "  ")["work_requirements"],
                {"description": ""},
            )

    def test_invalid_save_shows_error_dialog_and_preserves_saved_configuration(self):
        from trending_digest.ui import create_ui

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = save_configuration(root, {})
            original = (root / "conf.yaml").read_bytes()
            app = create_ui(root)
            callback = next(
                fn.fn for fn in app.fns.values() if fn.fn and fn.fn.__name__ == "save_form"
            )
            result = callback(config, "en", "Unsaved description", "../invalid")
            self.assertEqual(result[-1]["kind"], "error")
            self.assertEqual((root / "conf.yaml").read_bytes(), original)
            self.assertTrue(result[-2]["visible"])


if __name__ == "__main__":
    unittest.main()
