"""Deterministic model responses for offline integration and browser checks."""


def fake_analysis(repositories, config):
    focused = bool(config["work_requirements"]["description"])
    return {
        "results": [
            {
                "id": repo["name"],
                "purpose": f"Model introduction: {repo.get('description') or repo['name']}.",
                "highlights": ["Works with the capabilities documented in the README."],
                "score": (85 if "game-profiler" in repo["name"] else 10) if focused else 0,
                "reason": "Fits the described performance-analysis task." if focused else "",
                "use_case": "Inspect frame-time regressions in client builds." if focused else "",
            }
            for repo in repositories
        ]
    }
