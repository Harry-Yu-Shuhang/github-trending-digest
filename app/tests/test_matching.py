from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from model_fixtures import fake_analysis

from trending_digest.cli import generate
from trending_digest.config import validate_config
from trending_digest.matching import apply_requirements, selected_repositories
from trending_digest.service import run_generation, save_configuration


def repository(name, description):
    return {
        "name": name,
        "description": description,
        "url": "https://github.com/" + name,
        "language": "C++",
        "stars": 100,
        "stars_today": 5,
        "readme": {
            "excerpt": description,
            "url": "https://github.com/" + name + "#readme",
            "sha": "a" * 40,
            "status": "ok",
        },
    }


class ModelMatchingTests(unittest.TestCase):
    def config(self, description=""):
        return validate_config(
            {
                "llm": {"model": "test-model", "batch_size": 1},
                "work_requirements": {"description": description},
            }
        )

    def test_model_scores_drive_selection_and_summaries_without_literal_overlap(self):
        config = self.config("游戏客户端性能测试")
        repos = [
            repository("example/unrelated", "A learning assistant with test instructions"),
            repository("example/generic-trace", "A system timeline explorer"),
            repository("example/game-profiler", "A graphics analysis tool"),
        ]
        responses = [
            {
                "id": repo["name"],
                "purpose": "模型生成的仓库介绍",
                "highlights": ["来自 README 的亮点"],
                "score": score,
                "reason": "根据工作任务判断相关性",
                "use_case": "分析客户端帧时间回归",
            }
            for repo, score in zip(repos, [10, 60, 90], strict=True)
        ]
        snapshot = {"repositories": repos, "top_n": 2}
        with patch(
            "trending_digest.llm.request_analysis",
            side_effect=[{"results": [item]} for item in responses],
        ) as model:
            apply_requirements(snapshot, config)
        self.assertEqual(model.call_count, 3)
        self.assertEqual(
            [repo["name"] for repo in selected_repositories(snapshot)],
            ["example/game-profiler", "example/generic-trace"],
        )
        self.assertTrue(
            all(repo["summary"]["status"] == "model" for repo in snapshot["repositories"])
        )
        self.assertTrue(
            all(
                repo["summary"]["model"] == repo["work_match"]["model"] == "test-model"
                for repo in snapshot["repositories"]
            )
        )

    def test_empty_description_still_calls_model_for_introductions_and_disables_filter(self):
        config = self.config()
        snapshot = {
            "repositories": [repository("example/search", "Local document search")],
            "top_n": 25,
        }
        with patch("trending_digest.llm.request_analysis", side_effect=fake_analysis) as model:
            apply_requirements(snapshot, config)
        model.assert_called_once()
        self.assertEqual(len(selected_repositories(snapshot)), 1)
        self.assertNotIn("work_match", snapshot["repositories"][0])
        self.assertIn(
            "Model introduction", snapshot["repositories"][0]["summary"]["locales"]["en"]["purpose"]
        )

    def test_failed_batch_never_mutates_snapshot_or_falls_back_to_keywords(self):
        config = self.config("performance")
        snapshot = {
            "repositories": [
                repository("example/first", "performance profiler"),
                repository("example/second", "performance profiler"),
            ],
            "top_n": 25,
        }
        before = copy.deepcopy(snapshot)
        first = fake_analysis(snapshot["repositories"][:1], config)
        with patch("trending_digest.llm.request_analysis", side_effect=[first, {"results": []}]):
            with self.assertRaisesRegex(ValueError, "omitted"):
                apply_requirements(snapshot, config)
        self.assertEqual(snapshot, before)

    def test_cached_generation_reanalyzes_with_the_configured_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            for name in ("README.md", "docs/README.zh-CN.md"):
                (root / name).write_text("<!-- digest:start -->\n<!-- digest:end -->")
            config = self.config()
            save_configuration(root, config)
            page = Path(__file__).parent / "fixtures/trending.html"
            readme = {
                "status": "ok",
                "sha": "a" * 40,
                "url": "https://github.com/demo/agent-kit#readme",
                "text": "A source README documenting the actual capabilities of this toolkit.",
            }
            with (
                patch("trending_digest.readmes.fetch_readme", side_effect=lambda *_: dict(readme)),
                patch(
                    "trending_digest.llm.request_analysis",
                    side_effect=fake_analysis,
                ),
            ):
                generate(root, root / "conf.yaml", page)
            before = (root / "output/latest.md").read_bytes()
            config["work_requirements"]["description"] = "游戏性能测试"
            with patch(
                "trending_digest.llm.request_analysis", side_effect=ValueError("model failed")
            ):
                with self.assertRaisesRegex(ValueError, "model failed"):
                    run_generation(root, config, cached=True)
            self.assertEqual((root / "output/latest.md").read_bytes(), before)

    def test_unconfigured_model_fails_before_fetching(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            save_configuration(root, {})
            with patch("trending_digest.cli.fetch_html") as fetch:
                with self.assertRaisesRegex(ValueError, "llm.model"):
                    generate(root, root / "conf.yaml")
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
