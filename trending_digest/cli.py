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

from .core import (
    fetch_html,
    load_config,
    make_snapshot,
    parse_trending,
    previous_snapshot,
    trending_url,
)
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


def generate(root: Path, config_path: Path, html_path: Path | None = None) -> dict:
    config = load_config(config_path)
    html = html_path.read_text(encoding="utf-8") if html_path else fetch_html(trending_url(config))
    snapshot = make_snapshot(parse_trending(html), config, datetime.now().astimezone())
    day = snapshot["date"]
    previous = previous_snapshot(root, day, snapshot["source_url"])
    # Validate and render before touching published artifacts.
    readme = update_readme((root / "README.md").read_text(encoding="utf-8"), snapshot)
    digest = render_digest(snapshot, previous)
    atomic_write(root / report_path(day), digest)
    atomic_write(
        root / f"data/{day[:4]}/{day[5:7]}/{day}.json",
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write(root / "latest.md", digest)
    atomic_write(root / "daily/README.md", archive_index(root))
    atomic_write(root / "README.md", readme)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 GitHub Trending 中文技术快报")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--config", type=Path, help="默认使用 root/config.json")
    parser.add_argument("--html", type=Path, help="离线 HTML 输入，用于调试解析，不用于历史回填")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        snapshot = generate(args.root, args.config or args.root / "config.json", args.html)
    except (OSError, ValueError, KeyError, TypeError, URLError, ZoneInfoNotFoundError) as exc:
        logger.error("快报生成失败：%s", exc)
        return 1
    logger.info("已生成 %s 技术快报，共 %d 个项目", snapshot["date"], len(snapshot["repositories"]))
    return 0
