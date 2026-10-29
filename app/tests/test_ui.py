from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from trending_digest.config import validate_config
from trending_digest.service import save_configuration

HAS_GRADIO = importlib.util.find_spec("gradio") is not None


@unittest.skipUnless(HAS_GRADIO, "Install the ui extra to test Gradio")
class UiTests(unittest.TestCase):
    def test_form_roundtrip_keeps_all_configuration_fields(self):
        from trending_digest.ui import config_from_values, form_values

        config = validate_config(
            {
                "active_language": "zh-CN",
                "top_n": 7,
                "programming_language": "rust",
                "readme": {"workers": 2},
                "work_requirements": {
                    "enabled": True,
                    "description": "本地文档搜索",
                    "keywords": ["search", "搜索"],
                },
            }
        )
        self.assertEqual(config_from_values(form_values(config)), config)
        values = form_values(config)
        values[3] = 3.5
        with self.assertRaises(ValueError):
            config_from_values(values)

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


if __name__ == "__main__":
    unittest.main()
