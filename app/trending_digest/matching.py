"""Apply model-generated briefs and rank repositories by work relevance."""

from __future__ import annotations

import copy

from .llm import analyze_repositories


def has_work_requirements(snapshot: dict) -> bool:
    requirements = snapshot.get("work_requirements", {})
    return bool(requirements.get("description", "").strip())


def apply_requirements(snapshot: dict, config: dict) -> dict:
    repositories = analyze_repositories(snapshot["repositories"], config)
    snapshot["repositories"] = repositories
    snapshot["work_requirements"] = copy.deepcopy(config["work_requirements"])
    snapshot["analysis_model"] = config["llm"]["model"]
    return snapshot


def selected_repositories(snapshot: dict) -> list[dict]:
    repos = snapshot["repositories"]
    if has_work_requirements(snapshot):
        repos = sorted(
            (repo for repo in repos if repo.get("work_match", {}).get("useful")),
            key=lambda repo: -repo["work_match"].get("score", 0),
        )
    return repos[: snapshot["top_n"]]
