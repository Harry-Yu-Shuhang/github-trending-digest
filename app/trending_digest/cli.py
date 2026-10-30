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
from .html_report import html_outputs
from .llm import ensure_model_configured
from .matching import apply_requirements, selected_repositories
from .readmes import enrich_repositories
from .render import archive_index, render_digest, report_path, update_readme

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
    ensure_model_configured(config)
    html = html_path.read_text(encoding="utf-8") if html_path else fetch_html(trending_url(config))
    repositories = enrich_repositories(parse_trending(html), root, config, readme_dir)
    snapshot = make_snapshot(repositories, config, datetime.now().astimezone())
    apply_requirements(snapshot, config)
    publish_snapshot(root, snapshot)
    return snapshot


def publish_snapshot(root: Path, snapshot: dict) -> None:
    day = snapshot["date"]
    # Render the active language before touching published artifacts.
    outputs = {}
    locale = snapshot["active_language"]
    readme_path = root / "README.md" if locale == "en" else root / "docs/README.zh-CN.md"
    link_prefix = "output/" if locale == "en" else "../output/"
    outputs[readme_path] = update_readme(
        readme_path.read_text(encoding="utf-8"), snapshot, locale, link_prefix=link_prefix
    )
    output = root / "output"
    outputs[output / report_path(day, locale)] = render_digest(snapshot, locale)
    outputs[output / "latest.md"] = render_digest(snapshot, locale, "latest")
    outputs.update(html_outputs(output, snapshot))
    atomic_write(
        output / f"data/{day[:4]}/{day[5:7]}/{day}.json",
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
    )
    for path, content in outputs.items():
        atomic_write(path, content)
    atomic_write(output / "daily/README.md", archive_index(output, locale))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate README-based tech briefs in the configured active language"
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
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
        len(selected_repositories(snapshot)),
    )
    return 0
