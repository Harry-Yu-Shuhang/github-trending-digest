"""Fetch the real Trending page and preserve its order and measurement semantics."""

from __future__ import annotations

import re
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .config import load_config as load_config

USER_AGENT = "github-trending-digest/0.1 (+https://github.com/trending)"
NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def trending_url(config: dict) -> str:
    language = quote(config["programming_language"].strip().lower(), safe="")
    query = {"since": "daily"}
    if config["spoken_language"]:
        query["spoken_language_code"] = config["spoken_language"]
    return (
        "https://github.com/trending"
        + ("/" + language if language else "")
        + "?"
        + urlencode(query)
    )


def fetch_html(url: str, attempts: int = 3) -> str:
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("Fetching Trending failed")


def parse_count(text: str) -> int | None:
    """Missing values are unknown, never silently zero."""
    match = re.search(r"([\d,]+(?:\.\d+)?)\s*([kKmM]?)", text)
    if not match:
        return None
    multiplier = {"": 1, "k": 1000, "m": 1_000_000}[match[2].lower()]
    return int(float(match[1].replace(",", "")) * multiplier)


def parse_trending(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    repositories = []
    seen = set()
    for article in soup.select("article.Box-row"):
        anchor = article.select_one("h2 a[href]")
        if anchor is None:
            continue
        name = anchor["href"].strip("/")
        if not NAME.fullmatch(name) or name.split("/")[0] in {"sponsors", "topics", "collections"}:
            continue
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        description = article.select_one("p")
        language = article.select_one('[itemprop="programmingLanguage"]')
        stars = article.select_one('a[href$="/stargazers"]')
        forks = article.select_one('a[href$="/forks"]')
        daily = next(
            (
                span.get_text(" ", strip=True)
                for span in article.select("span")
                if re.fullmatch(r"[\d,.kKmM]+\s+stars?\s+today", span.get_text(" ", strip=True))
            ),
            "",
        )
        repositories.append(
            {
                "rank": len(repositories) + 1,
                "name": name,
                "url": "https://github.com/" + name,
                "description": description.get_text(" ", strip=True) if description else "",
                "language": language.get_text(strip=True) if language else None,
                "stars": parse_count(stars.get_text()) if stars else None,
                "forks": parse_count(forks.get_text()) if forks else None,
                "stars_today": parse_count(daily),
            }
        )
    if not repositories:
        raise ValueError(
            "Trending returned no repositories; page layout or access may have changed"
        )
    return repositories


def make_snapshot(repositories: list[dict], config: dict, now: datetime) -> dict:
    local = now.astimezone(ZoneInfo(config["timezone"]))
    return {
        "schema_version": 2,
        "date": local.date().isoformat(),
        "fetched_at": local.isoformat(timespec="seconds"),
        "timezone": config["timezone"],
        "source_url": trending_url(config),
        "top_n": config["top_n"],
        "default_language": config["default_language"],
        "languages": config["languages"],
        "repositories": repositories,
    }
