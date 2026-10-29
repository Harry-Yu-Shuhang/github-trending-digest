"""Read README content; reuse versioned bilingual notes or extract source passages."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml
from bs4 import BeautifulSoup

from .core import USER_AGENT

logger = logging.getLogger(__name__)
FEATURE_HEADING = re.compile(
    r"features?|highlights?|capabilit|what you get|what works|why|"
    r"功能|特性|特色|亮点|能力",
    re.IGNORECASE,
)
SKIP_HEADING = re.compile(
    r"table of contents|install|release|changelog|news|sponsor|license|contribut|"
    r"目录|安装|更新日志|赞助|许可|贡献",
    re.IGNORECASE,
)


def fetch_readme(repo: dict, timeout: int) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(f"https://api.github.com/repos/{repo['name']}/readme", headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                metadata = json.load(response)
            if metadata.get("encoding") != "base64":
                raise ValueError("README content is not available as base64")
            return {
                "sha": metadata["sha"],
                "url": metadata["html_url"],
                "path": metadata["path"],
                "status": "ok",
                "text": base64.b64decode(metadata["content"]).decode("utf-8"),
            }
        except HTTPError as exc:
            if exc.code == 404:
                return {"status": "missing", "url": repo["url"] + "#readme"}
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("README fetch failed")


def clean_readme(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^\n]*?\)", "", text)
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.select("script, style, img, svg, video, iframe"):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\[([^\]]*)\]\([^\n]*?\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    return text


def extract_passages(text: str, count: int, max_chars: int) -> tuple[str, list[str]]:
    """Extract only actual source text; never call this a translated summary."""
    text = clean_readme(text)
    intro, features = [], []
    section, blocked_level = "", 0
    for paragraph in re.split(r"\n\s*\n", text):
        for block in re.split(r"(?m)(?=^#{1,6}\s)", paragraph):
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            if lines[0].startswith("#"):
                level = len(lines[0]) - len(lines[0].lstrip("#"))
                if blocked_level and level <= blocked_level:
                    blocked_level = 0
                section = lines[0].lstrip("# ").strip()
                if not blocked_level and SKIP_HEADING.search(section):
                    blocked_level = level
                lines = lines[1:]
            if blocked_level:
                continue
            content = " ".join(line.strip() for line in lines).strip()
            content = re.sub(r"^[>\-*\s]+", "", content).strip()
            if not content or "|" in content or len(content) < 45:
                continue
            if len(content) > max_chars:
                content = content[:max_chars].rsplit(" ", 1)[0] + "…"
            if FEATURE_HEADING.search(section):
                features.append(content)
            else:
                intro.append(content)
    candidates = list(dict.fromkeys(intro + features))
    purpose = candidates[0] if candidates else ""
    highlights = list(dict.fromkeys(features + intro[1:]))
    highlights = [item for item in highlights if item != purpose][:count]
    return purpose, highlights


def load_curated(path: Path, languages: list[str]) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Invalid curated summary schema")
    projects = data.get("projects")
    if not isinstance(projects, dict):
        raise ValueError("Curated summaries must contain a projects mapping")
    for name, entry in projects.items():
        if not isinstance(entry, dict) or not re.fullmatch(
            r"[0-9a-f]{40}", str(entry.get("readme_sha", ""))
        ):
            raise ValueError(f"Missing README SHA for {name}")
        for locale in languages:
            summary = entry.get(locale, {})
            if not isinstance(summary.get("purpose"), str) or not summary["purpose"].strip():
                raise ValueError(f"Missing {locale} purpose for {name}")
            highlights = summary.get("highlights")
            if (
                not isinstance(highlights, list)
                or not 1 <= len(highlights) <= 5
                or any(not isinstance(item, str) or not item.strip() for item in highlights)
            ):
                raise ValueError(f"Invalid {locale} highlights for {name}")
    return {name.lower(): entry for name, entry in projects.items()}


def enrich_repositories(
    repos: list[dict], root: Path, config: dict, readme_dir: Path | None = None
) -> list[dict]:
    curated = (
        load_curated(root / config["summary"]["curated_file"], config["languages"])
        if config["summary"]["mode"] == "curated"
        else {}
    )

    def enrich(repo: dict) -> dict:
        repo = dict(repo)
        try:
            if readme_dir:
                directory = readme_dir / repo["name"]
                readme = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
                readme.update(
                    text=(directory / "README.md").read_text(encoding="utf-8"), status="ok"
                )
            else:
                readme = fetch_readme(repo, config["readme"]["timeout_seconds"])
        except (OSError, URLError, ValueError, KeyError) as exc:
            logger.warning("Could not read %s README: %s", repo["name"], exc)
            readme = {"status": "unavailable", "url": repo["url"] + "#readme"}
        text = readme.pop("text", "")
        repo["readme"] = readme
        entry = curated.get(repo["name"].lower())
        if (
            config["summary"]["mode"] == "curated"
            and readme["status"] == "ok"
            and entry
            and entry["readme_sha"] == readme["sha"]
        ):
            repo["summary"] = {
                "status": "curated",
                "locales": {
                    locale: {
                        "purpose": entry[locale]["purpose"],
                        "highlights": entry[locale]["highlights"][
                            : config["summary"]["highlights"]
                        ],
                    }
                    for locale in config["languages"]
                },
            }
        else:
            purpose, highlights = extract_passages(
                text[: config["readme"]["max_chars"]],
                config["summary"]["highlights"],
                350,
            )
            status = "extractive" if purpose else "unavailable"
            repo["summary"] = {
                "status": status,
                "needs_review": True,
                "locales": {
                    locale: {"purpose": purpose, "highlights": highlights}
                    for locale in config["languages"]
                },
            }
        return repo

    selected = repos[: config["top_n"]]
    with ThreadPoolExecutor(max_workers=config["readme"]["workers"]) as pool:
        return list(pool.map(enrich, selected)) + repos[len(selected) :]
