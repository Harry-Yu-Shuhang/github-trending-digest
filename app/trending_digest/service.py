"""Shared, validated operations for the UI and local launchers."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from threading import RLock

import yaml

from .cli import atomic_write, generate, publish_snapshot
from .config import load_config, validate_config
from .matching import apply_requirements
from .readmes import load_curated

OPERATIONS = RLock()


def profile_path(root: Path, name: str) -> Path:
    if (
        not isinstance(name, str)
        or not re.fullmatch(r"[\w -]{1,80}", name)
        or name != name.strip()
        or name.upper() in {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
        or re.fullmatch(r"(?:COM|LPT)[0-9¹²³]", name, re.IGNORECASE)
    ):
        raise ValueError("Profile name: use 1–80 letters, numbers, spaces, underscores or hyphens")
    path = root / "configs" / f"{name}.yaml"
    if not path.resolve().is_relative_to((root / "configs").resolve()):
        raise ValueError("Profile must stay inside configs/")
    return path


def list_profiles(root: Path) -> list[str]:
    names = []
    for path in (root / "configs").glob("*.yaml"):
        try:
            profile_path(root, path.stem)
        except ValueError:
            continue
        names.append(path.stem)
    return sorted(names, key=str.casefold)


def load_profile(root: Path, name: str) -> dict:
    with OPERATIONS:
        return load_config(profile_path(root, name))


def save_configuration(root: Path, config: dict, *, profile_name: str | None = None) -> dict:
    checked = validate_config(config)
    named_path = profile_path(root, profile_name) if profile_name is not None else None
    content = (
        "# Configuration for the local UI and report generator.\n"
        "# active_language options: en (English), zh-CN (简体中文). "
        "Controls the GUI and report language.\n"
        + yaml.safe_dump(checked, allow_unicode=True, sort_keys=False)
    )
    with OPERATIONS:
        if named_path is not None:
            atomic_write(named_path, content)
        atomic_write(root / "conf.yaml", content)
    return checked


def saved_snapshot(root: Path, config: dict) -> dict:
    paths = sorted((root / "output/data").glob("????/??/????-??-??.json"), reverse=True)
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
        readme = repo.setdefault(
            "readme", {"url": repo["url"] + "#readme", "status": "unavailable"}
        )
        # Older snapshots saved only summaries. Keep that evidence across locale changes.
        if not readme.get("excerpt"):
            readme["excerpt"] = "\n".join(
                value
                for note in repo.get("summary", {}).get("locales", {}).values()
                for value in [note.get("purpose", ""), *note.get("highlights", [])]
            )
        if (
            index >= config["top_n"]
            and not config["work_requirements"]["enabled"]
            and "summary" not in repo
        ):
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
    return apply_requirements(snapshot, config)


def run_generation(root: Path, config: dict, *, cached: bool = False) -> dict:
    with OPERATIONS:
        save_configuration(root, config)
        if cached:
            snapshot = saved_snapshot(root, load_config(root / "conf.yaml"))
            publish_snapshot(root, snapshot)
            return snapshot
        return generate(root, root / "conf.yaml")
