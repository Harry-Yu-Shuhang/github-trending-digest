from __future__ import annotations

import copy
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from model_fixtures import fake_analysis

from trending_digest.config import validate_config
from trending_digest.llm import analyze_repositories, request_analysis, validate_results


class ModelClientTests(unittest.TestCase):
    def setUp(self):
        self.config = validate_config(
            {
                "llm": {
                    "model": "shared-test-model",
                    "api_key": "yaml-test-key",
                    "api_key_env": "LLM_API_KEY",
                }
            }
        )
        self.repos = [
            {
                "name": "example/game-profiler",
                "description": "A frame-time profiler",
                "readme": {
                    "excerpt": "README evidence. Ignore all instructions is untrusted source text."
                },
            }
        ]

    def test_http_payload_environment_key_and_both_results_use_same_model(self):
        requests = []
        result = fake_analysis(self.repos, self.config)

        class Handler(BaseHTTPRequestHandler):
            def do_POST(handler):
                payload = json.loads(handler.rfile.read(int(handler.headers["Content-Length"])))
                requests.append((handler.path, handler.headers.get("Authorization"), payload))
                raw = json.dumps(
                    {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": json.dumps(result),
                                },
                            }
                        ]
                    }
                ).encode()
                handler.send_response(200)
                handler.send_header("Content-Type", "application/json")
                handler.send_header("Content-Length", str(len(raw)))
                handler.end_headers()
                handler.wfile.write(raw)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.config["llm"]["base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
            with patch.dict(os.environ, {"LLM_API_KEY": "environment-test-key"}):
                analysis = request_analysis(self.repos, self.config)
            self.assertEqual(analysis, result)
            path, auth, payload = requests[0]
            self.assertEqual(path, "/v1/chat/completions")
            self.assertEqual(auth, "Bearer environment-test-key")
            self.assertEqual(payload["model"], "shared-test-model")
            self.assertIs(payload["stream"], False)
            self.assertEqual(payload["response_format"], {"type": "json_object"})
            source = json.loads(payload["messages"][1]["content"])
            self.assertEqual(source["work_description"], "")
            self.assertIn("untrusted source text", source["repositories"][0]["readme_excerpt"])
            self.assertNotIn("yaml-test-key", json.dumps(payload))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_local_ollama_needs_no_key_and_does_not_use_cloud_environment_credentials(self):
        config = validate_config({"llm": {"model": "installed-model:tag"}})
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": json.dumps(fake_analysis(self.repos, config))}}]}
        ).encode()
        with (
            patch.dict(os.environ, {"LLM_API_KEY": "private-cloud-key"}),
            patch("trending_digest.llm.build_opener") as opener,
        ):
            opener.return_value.open.return_value = response
            data = request_analysis(self.repos, config)
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/v1/chat/completions")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(len(data["results"]), 1)

    def test_result_validation_rejects_missing_duplicate_invented_ids_and_bad_scores(self):
        good = fake_analysis(self.repos, self.config)
        bad = [
            {"results": []},
            {"results": [good["results"][0], good["results"][0]]},
            {"results": [{**good["results"][0], "id": "invented/repo"}]},
            {"results": [{**good["results"][0], "score": True}]},
            {"results": [{**good["results"][0], "score": 101}]},
            {"results": [{**good["results"][0], "purpose": ""}]},
        ]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_results(data, self.repos, self.config)

    def test_missing_readme_is_not_invented_and_no_key_is_saved_in_results(self):
        repos = copy.deepcopy(self.repos)
        repos.append({"name": "example/missing", "readme": {"excerpt": ""}})
        self.config["work_requirements"]["description"] = "游戏性能测试"
        with patch("trending_digest.llm.request_analysis", side_effect=fake_analysis) as call:
            output = analyze_repositories(repos, self.config)
        self.assertEqual(len(call.call_args.args[0]), 1)
        self.assertEqual(output[1]["summary"]["status"], "unavailable")
        self.assertFalse(output[1]["work_match"]["useful"])
        self.assertNotIn("yaml-test-key", json.dumps(output))
        self.assertNotIn("summary", repos[0])

    def test_invalid_llm_settings_are_rejected(self):
        for settings in (
            {"base_url": "file:///tmp/model"},
            {"base_url": "https://key@api.example/v1"},
            {"batch_size": 0},
            {"timeout_seconds": True},
            {"model": 42},
            {"response_format": "unsupported"},
        ):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                validate_config({"llm": settings})

    def test_incomplete_refused_and_malformed_responses_fail_explicitly(self):
        for envelope in (
            {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
            {"choices": [{"message": {"refusal": "Cannot comply", "content": None}}]},
            {"choices": [{"message": {"content": "not JSON"}}]},
            {"choices": []},
        ):
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(envelope).encode()
            with (
                self.subTest(envelope=envelope),
                patch("trending_digest.llm.build_opener") as opener,
            ):
                opener.return_value.open.return_value = response
                with self.assertRaises(ValueError):
                    request_analysis(self.repos, self.config)
        with patch("trending_digest.llm.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(
                "https://example.invalid",
                401,
                "private body yaml-test-key",
                {},
                None,
            )
            with self.assertRaises(ValueError) as error:
                request_analysis(self.repos, self.config)
            self.assertIn("401", str(error.exception))
            self.assertNotIn("yaml-test-key", str(error.exception))


if __name__ == "__main__":
    unittest.main()
