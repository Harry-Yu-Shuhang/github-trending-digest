from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from zoneinfo import ZoneInfoNotFoundError

import yaml

from .core import (
    fetch_html,
    load_config,
    make_snapshot,
    parse_trending,
    trending_url,
)
from .readmes import enrich_repositories
from .render import archive_index, localized_name, render_digest, report_path, update_readme

logger = logging.getLogger(__name__)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as file:
            temporary = Path(file.name)
            file.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def generate(
    root: Path, config_path: Path, html_path: Path | None = None, readme_dir: Path | None = None
) -> dict:
    config = load_config(config_path)
    html = html_path.read_text(encoding="utf-8") if html_path else fetch_html(trending_url(config))
    repositories = enrich_repositories(parse_trending(html), root, config, readme_dir)
    snapshot = make_snapshot(repositories, config, datetime.now().astimezone())
    day = snapshot["date"]
    # Validate all languages and render before touching published artifacts.
    outputs = {}
    default = config["default_language"]
    for locale in config["languages"]:
        readme_path = root / localized_name("README", locale, default)
        outputs[readme_path] = update_readme(
            readme_path.read_text(encoding="utf-8"), snapshot, locale
        )
        outputs[root / report_path(day, locale, default)] = render_digest(snapshot, locale)
        outputs[root / localized_name("latest", locale, default)] = render_digest(
            snapshot, locale, "latest"
        )
    atomic_write(
        root / f"data/{day[:4]}/{day[5:7]}/{day}.json",
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
    )
    for path, content in outputs.items():
        atomic_write(path, content)
    for locale in config["languages"]:
        atomic_write(
            root / "daily" / localized_name("README", locale, default),
            archive_index(root, locale, config["languages"], default),
        )
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate bilingual README-based GitHub tech briefs"
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--config", type=Path, help="Defaults to root/conf.yaml")
    parser.add_argument("--html", type=Path, help="Offline Trending HTML; uses the current date")
    parser.add_argument(
        "--readme-dir", type=Path, help="Offline owner/repo README.md and metadata.json"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        snapshot = generate(
            args.root, args.config or args.root / "conf.yaml", args.html, args.readme_dir
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        URLError,
        ZoneInfoNotFoundError,
        yaml.YAMLError,
    ) as exc:
        logger.error("Brief generation failed: %s", exc)
        return 1
    logger.info(
        "Generated %s brief with %d project notes",
        snapshot["date"],
        min(snapshot["top_n"], len(snapshot["repositories"])),
    )
    return 0
