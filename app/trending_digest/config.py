from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import yaml

SUPPORTED_LANGUAGES = {"en", "zh-CN"}


def bounded_int(value: object, minimum: int, maximum: int, name: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")


def load_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return validate_config(config)


def validate_config(config: object) -> dict:
    if not isinstance(config, dict):
        raise ValueError("conf.yaml must contain a mapping")
    config = dict(config)
    if "default_language" in config:
        legacy = config.pop("default_language")
        config.pop("languages", None)
        if "active_language" in config and config["active_language"] != legacy:
            raise ValueError("Conflicting active_language and legacy language settings")
        config["active_language"] = legacy
    defaults = {
        "active_language": "en",
        "programming_language": "",
        "spoken_language": "",
        "top_n": 25,
        "timezone": "Asia/Shanghai",
        "readme": {},
        "summary": {},
        "work_requirements": {},
        "llm": {},
    }
    if config.keys() - defaults.keys():
        raise ValueError(f"Unknown configuration keys: {config.keys() - defaults.keys()}")
    config = {**defaults, **config}
    if (
        not isinstance(config["active_language"], str)
        or config["active_language"] not in SUPPORTED_LANGUAGES
    ):
        raise ValueError("active_language must be en or zh-CN")
    bounded_int(config["top_n"], 1, 25, "top_n")
    for name in ("programming_language", "spoken_language", "timezone"):
        if not isinstance(config[name], str):
            raise ValueError(f"{name} must be a string")
    ZoneInfo(config["timezone"])
    for name, values in {
        "readme": {"max_chars": 24000, "timeout_seconds": 30, "workers": 4},
        "summary": {
            "mode": "model",
            "curated_file": "summaries.yaml",
            "fallback": "extractive",
            "highlights": 3,
        },
    }.items():
        if not isinstance(config[name], dict) or config[name].keys() - values.keys():
            raise ValueError(f"Invalid {name} configuration")
        config[name] = {**values, **config[name]}
    bounded_int(config["readme"]["max_chars"], 1000, 100000, "readme.max_chars")
    bounded_int(config["readme"]["timeout_seconds"], 1, 120, "readme.timeout_seconds")
    bounded_int(config["readme"]["workers"], 1, 8, "readme.workers")
    bounded_int(config["summary"]["highlights"], 1, 5, "summary.highlights")
    if config["summary"]["mode"] not in {"model", "curated", "extractive"}:
        raise ValueError("summary.mode must be model, curated or extractive")
    if config["summary"]["fallback"] != "extractive":
        raise ValueError("summary.fallback must be extractive")
    if (
        not isinstance(config["summary"]["curated_file"], str)
        or not config["summary"]["curated_file"].strip()
    ):
        raise ValueError("summary.curated_file must be a nonempty string")
    requirements = config["work_requirements"]
    requirement_defaults = {
        "enabled": False,
        "description": "",
        "keywords": [],
        "exclude_keywords": [],
        "min_matches": 1,
    }
    if not isinstance(requirements, dict) or requirements.keys() - requirement_defaults.keys():
        raise ValueError("Invalid work_requirements configuration")
    requirements = {**requirement_defaults, **requirements}
    if type(requirements["enabled"]) is not bool:
        raise ValueError("work_requirements.enabled must be a boolean")
    if not isinstance(requirements["description"], str):
        raise ValueError("work_requirements.description must be a string")
    for key in ("keywords", "exclude_keywords"):
        values = requirements[key]
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(f"work_requirements.{key} must be a list of nonempty strings")
        unique = {}
        for value in values:
            unique.setdefault(value.strip().casefold(), value.strip())
        requirements[key] = list(unique.values())
    bounded_int(requirements["min_matches"], 1, 100, "work_requirements.min_matches")
    description = requirements["description"].strip()
    # Older named profiles may contain only explicit keywords. Migrate once on load.
    if not description and requirements["enabled"] and requirements["keywords"]:
        description = ", ".join(requirements["keywords"])
    config["work_requirements"] = {"description": description}
    model_defaults = {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "",
        "api_key": "",
        "api_key_env": "",
        "timeout_seconds": 600,
        "batch_size": 1,
        "readme_max_chars": 4000,
        "response_format": "json_object",
    }
    if not isinstance(config["llm"], dict) or config["llm"].keys() - model_defaults.keys():
        raise ValueError("Invalid llm configuration")
    config["llm"] = {**model_defaults, **config["llm"]}
    for name in ("base_url", "model", "api_key", "api_key_env", "response_format"):
        if not isinstance(config["llm"][name], str):
            raise ValueError(f"llm.{name} must be a string")
    endpoint = urlsplit(config["llm"]["base_url"])
    if (
        endpoint.scheme not in {"https", "http"}
        or not endpoint.hostname
        or endpoint.username
        or endpoint.password
        or endpoint.query
        or endpoint.fragment
    ):
        raise ValueError("llm.base_url must be an HTTP(S) API root without credentials or query")
    bounded_int(config["llm"]["timeout_seconds"], 1, 600, "llm.timeout_seconds")
    bounded_int(config["llm"]["batch_size"], 1, 10, "llm.batch_size")
    bounded_int(config["llm"]["readme_max_chars"], 1000, 50000, "llm.readme_max_chars")
    if config["llm"]["response_format"] not in {"json_object", "json_schema", "text"}:
        raise ValueError("llm.response_format must be json_object, json_schema or text")
    return config
