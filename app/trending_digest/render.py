"""Localized project briefs, centered on README-backed purposes and highlights."""

from __future__ import annotations

import html
import re
from pathlib import Path

from .matching import has_work_requirements, selected_repositories

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
        "matched": "Matched work keywords",
        "relevance": "Work relevance",
        "direct": "Directly relevant",
        "transferable": "Potentially reusable",
        "domain_and_capability": "Matches your field and work tasks",
        "transferable_capability": "Provides a tool capability reusable in your work",
        "project_purpose": "The project purpose matches your work focus",
        "specific_terms": "Matches specific terms in your description",
        "model": "AI-generated introduction based on the source README; not independently tested.",
        "use_case": "How you could use it",
        "no_matches": "No repositories matched these work requirements. "
        "Try a different work description or leave it empty to include all projects.",
        "extractive": "README excerpts · summary pending in the selected language. "
        "Source language preserved.",
        "unavailable": "README unavailable; no project claims have been generated.",
        "pending": "No saved notes in this language. Fetch the README to prepare source excerpts.",
        "footer": "Project capabilities are summarized from the linked READMEs, not independently "
        "tested. Daily stars come from GitHub Trending at capture time.",
    },
    "zh-CN": {
        "matched": "匹配工作需求的关键词",
        "relevance": "工作相关性",
        "direct": "直接相关",
        "transferable": "可迁移使用",
        "domain_and_capability": "同时覆盖工作领域与任务方向",
        "transferable_capability": "具备可用于当前工作的通用工具能力",
        "project_purpose": "项目主要用途与工作方向相符",
        "specific_terms": "命中描述中的具体技术词",
        "model": "由大模型根据 README 生成，能力与适用性未经独立实测。",
        "use_case": "可以怎么用",
        "no_matches": "没有仓库符合当前工作内容，可换一种描述，或清空工作内容查看全部项目。",
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


def work_context(snapshot: dict, locale: str) -> list[str]:
    requirements = snapshot.get("work_requirements", {})
    if not has_work_requirements(snapshot):
        return []
    return [requirements["description"]]


def match_explanation(repo: dict, locale: str) -> str:
    match = repo["work_match"]
    copy = COPY[locale]
    if match.get("method") == "llm":
        return f"{copy[match['level']]} · {match['score']}/100 · {match['reason']}" + (
            f" · {copy['use_case']}: {match['use_case']}" if match.get("use_case") else ""
        )
    terms = ", ".join(match["matched_keywords"][:8])
    if "score" not in match:
        return terms
    return f"{copy[match['level']]} · {match['score']}/100 · {copy[match['reason']]}" + (
        f" · {terms}" if terms else ""
    )


def render_digest(snapshot: dict, locale: str | None = None, stem: str | None = None) -> str:
    locale = locale or snapshot["active_language"]
    copy = COPY[locale]
    repos = selected_repositories(snapshot)
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
    for context in work_context(snapshot, locale):
        lines.extend([f"> {safe_text(context)}", ""])
    if not repos and has_work_requirements(snapshot):
        lines.extend([copy["no_matches"], ""])
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
        if "work_match" in repo:
            matched = match_explanation(repo, locale)
            lines.extend([f"**{copy['relevance']}**: {safe_text(matched)}", ""])
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


def update_readme(
    readme: str, snapshot: dict, locale: str | None = None, *, link_prefix: str = ""
) -> str:
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
        f"[{copy['read']}]({link_prefix}{report_path(snapshot['date'], locale)}) · "
        f"[{copy['all']}]({link_prefix}daily/README.md)",
        "",
    ]
    for repo in selected_repositories(snapshot)[:3]:
        text = repo["summary"]["locales"][locale]["purpose"]
        if repo["summary"]["status"] in {"curated", "model"}:
            lines.append(f"- **[{repo['name']}]({repo['url']})** — {safe_text(text)}")
        else:
            lines.append(f"- [{repo['name']}]({repo['url']}) · {copy[repo['summary']['status']]}")
    lines.extend(["", end])
    return readme[: readme.index(start)] + "\n".join(lines) + readme[readme.index(end) + len(end) :]
