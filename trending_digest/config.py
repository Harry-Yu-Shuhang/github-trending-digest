from __future__ import annotations

from pathlib import Path
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
            "mode": "curated",
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
    if config["summary"]["mode"] not in {"curated", "extractive"}:
        raise ValueError("summary.mode must be curated or extractive")
    if config["summary"]["fallback"] != "extractive":
        raise ValueError("summary.fallback must be extractive")
    if (
        not isinstance(config["summary"]["curated_file"], str)
        or not config["summary"]["curated_file"].strip()
    ):
        raise ValueError("summary.curated_file must be a nonempty string")
    return config
