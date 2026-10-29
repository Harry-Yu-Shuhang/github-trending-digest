"""Shared, validated operations for the UI and local launchers."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock

import yaml

from .cli import atomic_write, generate, publish_snapshot
from .config import load_config, validate_config
from .readmes import load_curated

OPERATIONS = RLock()


def save_configuration(root: Path, config: dict) -> dict:
    checked = validate_config(config)
    with OPERATIONS:
        atomic_write(
            root / "conf.yaml",
            "# Configuration for the local UI and report generator.\n"
            + yaml.safe_dump(checked, allow_unicode=True, sort_keys=False),
        )
    return checked


def saved_snapshot(root: Path, config: dict) -> dict:
    paths = sorted((root / "data").glob("????/??/????-??-??.json"), reverse=True)
    if not paths:
        raise ValueError("No saved snapshot. Generate a fresh report first.")
    snapshot = copy.deepcopy(json.loads(paths[0].read_text(encoding="utf-8")))
    locale = config["active_language"]
    curated = (
        load_curated(root / config["summary"]["curated_file"], [locale])
        if config["summary"]["mode"] == "curated"
        else {}
    )
    snapshot.pop("default_language", None)
    snapshot.pop("languages", None)
    snapshot.update(schema_version=3, active_language=locale, top_n=config["top_n"])
    for index, repo in enumerate(snapshot["repositories"]):
        if index >= config["top_n"]:
            repo.pop("summary", None)
            continue
        entry = curated.get(repo["name"].lower())
        old = repo.get("summary", {})
        if entry and entry["readme_sha"] == repo.get("readme", {}).get("sha"):
            summary = {"status": "curated", "locales": {locale: copy.deepcopy(entry[locale])}}
        elif locale in old.get("locales", {}) and (
            config["summary"]["mode"] == "curated" or old["status"] == "extractive"
        ):
            summary = {**old, "locales": {locale: copy.deepcopy(old["locales"][locale])}}
        else:
            summary = {
                "status": "pending",
                "needs_review": True,
                "locales": {locale: {"purpose": "", "highlights": []}},
            }
        summary["locales"][locale]["highlights"] = summary["locales"][locale]["highlights"][
            : config["summary"]["highlights"]
        ]
        repo["summary"] = summary
        repo.setdefault("readme", {"url": repo["url"] + "#readme", "status": "unavailable"})
    return snapshot


def run_generation(root: Path, config: dict, *, cached: bool = False) -> dict:
    with OPERATIONS:
        save_configuration(root, config)
        if cached:
            snapshot = saved_snapshot(root, load_config(root / "conf.yaml"))
            publish_snapshot(root, snapshot)
            return snapshot
        return generate(root, root / "conf.yaml")
