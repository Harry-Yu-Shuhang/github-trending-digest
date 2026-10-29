"""Explainable work-requirement matching, without changing Trending order."""

from __future__ import annotations

import copy
import re


def match_repository(repo: dict, requirements: dict) -> dict:
    parts = [repo.get("name", ""), repo.get("description", ""), repo.get("language") or ""]
    parts.append(repo.get("readme", {}).get("excerpt", ""))
    for note in repo.get("summary", {}).get("locales", {}).values():
        parts.extend([note.get("purpose", ""), *note.get("highlights", [])])
    corpus = "\n".join(parts).casefold()

    def contains(term: str) -> bool:
        term = term.casefold()
        pattern = re.escape(term)
        if re.match(r"[a-z0-9]", term):
            pattern = r"(?<![a-z0-9])" + pattern
        if re.search(r"[a-z0-9]$", term):
            pattern += r"(?![a-z0-9])"
        return re.search(pattern, corpus) is not None

    matched = [term for term in requirements["keywords"] if contains(term)]
    excluded = [term for term in requirements["exclude_keywords"] if contains(term)]
    return {
        "useful": len(matched) >= requirements["min_matches"] and not excluded,
        "matched_keywords": matched,
        "excluded_keywords": excluded,
    }


def apply_requirements(snapshot: dict, config: dict) -> dict:
    requirements = copy.deepcopy(config["work_requirements"])
    snapshot["work_requirements"] = requirements
    for repo in snapshot["repositories"]:
        repo.pop("work_match", None)
        if requirements["enabled"]:
            repo["work_match"] = match_repository(repo, requirements)
    return snapshot


def selected_repositories(snapshot: dict) -> list[dict]:
    repos = snapshot["repositories"]
    if snapshot.get("work_requirements", {}).get("enabled"):
        repos = [repo for repo in repos if repo.get("work_match", {}).get("useful")]
    return repos[: snapshot["top_n"]]
