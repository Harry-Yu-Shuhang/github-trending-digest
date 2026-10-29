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
    if not isinstance(config, dict):
        raise ValueError("conf.yaml must contain a mapping")
    defaults = {
        "default_language": "en",
        "languages": ["en", "zh-CN"],
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
    locales = config["languages"]
    if (
        not isinstance(locales, list)
        or not locales
        or any(not isinstance(item, str) or item not in SUPPORTED_LANGUAGES for item in locales)
        or len(set(locales)) != len(locales)
    ):
        raise ValueError("languages must contain unique values from en, zh-CN")
    if config["default_language"] not in locales:
        raise ValueError("default_language must be included in languages")
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
    if not isinstance(config["summary"]["curated_file"], str):
        raise ValueError("summary.curated_file must be a string")
    return config
