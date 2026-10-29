"""Localized project briefs, centered on README-backed purposes and highlights."""

from __future__ import annotations

import html
import re
from pathlib import Path

COPY = {
    "en": {
        "title": "GitHub Tech Brief",
        "archive": "Brief archive",
        "latest": "Latest brief",
        "read": "Read this issue",
        "all": "Previous issues",
        "purpose": "What it does",
        "highlights": "Highlights",
        "source": "Source README",
        "captured": "Captured",
        "projects": "projects, explained from their READMEs.",
        "stars": "stars",
        "today": "{count} today",
        "unknown": "Not specified",
        "extractive": "README excerpts · summary pending in the selected language. "
        "Source language preserved.",
        "unavailable": "README unavailable; no project claims have been generated.",
        "pending": "No saved notes in this language. Fetch the README to prepare source excerpts.",
        "footer": "Project capabilities are summarized from the linked READMEs, not independently "
        "tested. Daily stars come from GitHub Trending at capture time.",
    },
    "zh-CN": {
        "title": "GitHub 技术快报",
        "archive": "快报归档",
        "latest": "最新一期",
        "read": "阅读本期",
        "all": "历史快报",
        "purpose": "这是做什么的",
        "highlights": "有什么亮点",
        "source": "来源 README",
        "captured": "采集时间",
        "projects": "个项目，从 README 了解用途与亮点。",
        "stars": "Star",
        "today": "今日新增 {count} Star",
        "unknown": "未标注",
        "extractive": "README 原文摘录 · 当前语言摘要待补充，以下保留来源语言。",
        "unavailable": "暂时无法读取 README，未生成项目能力介绍。",
        "pending": "已保存的数据中没有该语言的摘要，请重新抓取 README 生成原文摘录。",
        "footer": "项目能力概括自所链接的 README，未经独立实测。"
        "今日新增 Star 来自采集时的 GitHub Trending。",
    },
}


def safe_text(text: str) -> str:
    text = html.escape(" ".join(text.split()), quote=False)
    return re.sub(r"([\\`*_{\[\]()|#!])", r"\\\1", text)


def number(value: int | None, prefix: str = "") -> str:
    return "—" if value is None else f"{prefix}{value:,}"


def localized_name(stem: str, locale: str, default: str = "en") -> str:
    return f"{stem}{'' if locale == default else '.' + locale}.md"


def report_path(day: str, locale: str = "en", default: str = "en") -> str:
    return f"daily/{day[:4]}/{day[5:7]}/{localized_name(day, locale, default)}"


def render_digest(snapshot: dict, locale: str | None = None, stem: str | None = None) -> str:
    locale = locale or snapshot["active_language"]
    copy = COPY[locale]
    repos = snapshot["repositories"][: snapshot["top_n"]]
    lines = [
        f"# {copy['title']} · {snapshot['date']}",
        "",
        "English" if locale == "en" else "简体中文",
        "",
        f"{len(repos)} {copy['projects']}",
        "",
        f"> {copy['captured']}: {snapshot['fetched_at']} · "
        f"[GitHub Trending]({snapshot['source_url']})",
        "",
    ]
    for repo in repos:
        summary = repo["summary"]
        text = summary["locales"][locale]
        lines.extend(
            [
                f"## [{repo['name']}]({repo['url']})",
                "",
                f"{safe_text(repo['language'] or copy['unknown'])} · "
                f"{number(repo['stars'])} {copy['stars']} · "
                + copy["today"].format(count=number(repo["stars_today"], "+")),
                "",
            ]
        )
        if summary["status"] != "curated":
            lines.extend([f"> {copy[summary['status']]}", ""])
        if text["purpose"]:
            lines.extend([f"**{copy['purpose']}**", "", safe_text(text["purpose"]), ""])
        if text["highlights"]:
            lines.extend([f"**{copy['highlights']}**", ""])
            lines.extend(f"- {safe_text(item)}" for item in text["highlights"])
            lines.append("")
        lines.extend([f"[{copy['source']}]({repo['readme']['url']})", ""])
    lines.extend(["---", "", copy["footer"], ""])
    return "\n".join(lines)


def archive_index(root: Path, locale: str) -> str:
    days = sorted(
        (path.stem for path in (root / "data").glob("????/??/????-??-??.json")), reverse=True
    )
    lines = [f"# {COPY[locale]['archive']}", ""]
    for day in days:
        path = report_path(day, locale).removeprefix("daily/")
        if (root / "daily" / path).exists():
            lines.append(f"- [{day}]({path})")
    return "\n".join(lines) + "\n"


def update_readme(readme: str, snapshot: dict, locale: str | None = None) -> str:
    locale = locale or snapshot["active_language"]
    start, end = "<!-- digest:start -->", "<!-- digest:end -->"
    if (
        readme.count(start) != 1
        or readme.count(end) != 1
        or readme.index(start) > readme.index(end)
    ):
        raise ValueError("README must contain exactly one ordered digest marker pair")
    copy = COPY[locale]
    lines = [
        start,
        "",
        f"### {snapshot['date']} · {copy['latest']}",
        "",
        f"[{copy['read']}]({report_path(snapshot['date'], locale)}) · "
        f"[{copy['all']}](daily/README.md)",
        "",
    ]
    for repo in snapshot["repositories"][: min(snapshot["top_n"], 3)]:
        text = repo["summary"]["locales"][locale]["purpose"]
        if repo["summary"]["status"] == "curated":
            lines.append(f"- **[{repo['name']}]({repo['url']})** — {safe_text(text)}")
        else:
            lines.append(f"- [{repo['name']}]({repo['url']}) · {copy[repo['summary']['status']]}")
    lines.extend(["", end])
    return readme[: readme.index(start)] + "\n".join(lines) + readme[readme.index(end) + len(end) :]
