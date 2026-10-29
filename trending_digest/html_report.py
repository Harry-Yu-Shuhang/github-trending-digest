"""Portable, accessible HTML editions of the source-backed project briefs."""

from __future__ import annotations

import math
import re
from datetime import date
from html import escape
from importlib.resources import files
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

from .render import COPY, number

TEXT = {
    "en": {
        "brand": "The Trending Brief",
        "edition": "AN OPEN-SOURCE FIELD GUIDE",
        "title": "Good projects.<br>A closer look.",
        "intro": "What today’s open-source projects do, and the ideas that make them stand out. "
        "Read the essentials. Follow the source.",
        "latest": "Latest issue",
        "archive": "Archive",
        "issue": "Issue",
        "projects": "projects",
        "minutes": "min read",
        "languages": "languages",
        "search": "Search projects, ideas, or features…",
        "search_label": "Search this issue",
        "filter": "Filter by programming language",
        "all": "All technologies",
        "count": "{visible} of {total} projects",
        "reset": "Clear filters",
        "jump": "Jump to a project",
        "contents": "IN THIS ISSUE",
        "read": "Read the brief",
        "print": "Print / Save PDF",
        "theme": "Toggle dark mode",
        "skip": "Skip to projects",
        "empty": "No projects match your search.",
        "empty_hint": "Try another phrase or language.",
        "purpose": "THE IDEA",
        "highlights": "WHAT STANDS OUT",
        "source": "Read the README",
        "repository": "Repository",
        "today": "today",
        "unknown": "Unspecified",
        "source_note": "FROM THE SOURCE",
        "source_description": "Each note starts with the "
        "project’s README. Capabilities are described by the authors, not independently tested.",
        "archive_title": "Worth keeping.<br>Easy to revisit.",
        "archive_intro": "Past issues, with the same focus: "
        "what a project does and why it is interesting.",
        "archive_label": "PAST ISSUES",
        "back": "Back to top",
        "source_link": "GitHub Trending",
    },
    "zh-CN": {
        "brand": "开源技术快报",
        "edition": "发现开源项目，读懂技术亮点",
        "title": "发现好项目，<br>再多看一眼。",
        "intro": "从项目 README 出发，读懂它能做什么、有哪些值得关注的想法。先读重点，再看原文。",
        "latest": "最新一期",
        "archive": "历史快报",
        "issue": "本期日期",
        "projects": "个项目",
        "minutes": "分钟阅读",
        "languages": "种语言",
        "search": "搜索项目、用途或功能亮点…",
        "search_label": "搜索本期快报",
        "filter": "按编程语言筛选",
        "all": "全部技术语言",
        "count": "显示 {visible} / {total} 个项目",
        "reset": "清除筛选",
        "jump": "跳转到项目",
        "contents": "本期阅读目录",
        "read": "阅读本期",
        "print": "打印 / 保存 PDF",
        "theme": "切换深色模式",
        "skip": "跳转到项目内容",
        "empty": "没有找到匹配的项目。",
        "empty_hint": "试试其他关键词或编程语言。",
        "purpose": "这是做什么的",
        "highlights": "有什么亮点",
        "source": "阅读 README",
        "repository": "项目仓库",
        "today": "今日新增",
        "unknown": "未标注",
        "source_note": "从原文出发",
        "source_description": "每项介绍均基于项目 README。功能描述来自项目作者，未经独立实测。",
        "archive_title": "好项目，<br>值得再读一次。",
        "archive_intro": "回看往期快报，了解项目用途，以及那些值得关注的技术想法。",
        "archive_label": "往期快报",
        "back": "返回顶部",
        "source_link": "GitHub Trending",
    },
}

STAR = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path '
    'd="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9Z"/></svg>'
)
ARROW = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg>'


def html_name(stem: str, locale: str, default: str) -> str:
    return f"{stem}{'' if locale == default else '.' + locale}.html"


def safe_url(value: str) -> str:
    parsed = urlsplit(value)
    return (
        escape(value, quote=True)
        if parsed.scheme == "https" and parsed.hostname == "github.com"
        else "#"
    )


def locale_links(snapshot: dict, locale: str, stem: str) -> str:
    labels = {"en": "EN", "zh-CN": "中文"}
    target = stem + ".html" if stem in {"index", "archive"} else html_name(stem, locale, "en")
    return (
        f'<nav class="locale-switch" aria-label="Language"><a href="{target}" '
        f'lang="{locale}" aria-current="page">{labels[locale]}</a></nav>'
    )


def document(
    snapshot: dict,
    locale: str,
    *,
    stem: str,
    prefix: str,
    content: str,
    title: str,
    intro: str,
    page_kind: str,
    stats: str,
) -> str:
    text = TEXT[locale]
    resources = files("trending_digest").joinpath("templates")
    template = Template(resources.joinpath("report.html").read_text(encoding="utf-8"))
    day = date.fromisoformat(snapshot["date"])
    display_date = (
        day.strftime("%B %d, %Y")
        if locale == "en"
        else f"{day.year} 年 {day.month} 月 {day.day} 日"
    )
    return template.substitute(
        locale=locale,
        page_title=escape(f"{text['brand']} · {snapshot['date']}"),
        description=escape(intro, quote=True),
        css=resources.joinpath("report.css").read_text(encoding="utf-8"),
        script=resources.joinpath("report.js").read_text(encoding="utf-8"),
        brand=text["brand"],
        latest=text["latest"],
        archive=text["archive"],
        latest_href=prefix + "index.html",
        archive_href=prefix + "archive.html",
        locale_links=locale_links(snapshot, locale, stem),
        theme=text["theme"],
        print_label=text["print"],
        skip=text["skip"],
        edition=text["edition"],
        date=escape(display_date),
        iso_date=snapshot["date"],
        title=title,
        intro=escape(intro),
        stats=stats,
        content=content,
        page_kind=page_kind,
        back=text["back"],
        source_link=text["source_link"],
        source_url=safe_url(snapshot["source_url"]),
        footer=escape(COPY[locale]["footer"]),
    )


def render_html(snapshot: dict, locale: str | None = None, *, latest: bool = False) -> str:
    locale = locale or snapshot["active_language"]
    text = TEXT[locale]
    repos = snapshot["repositories"][: snapshot["top_n"]]
    cards, contents, jumps = [], [], []
    for index, repo in enumerate(repos, 1):
        summary = repo["summary"]
        note = summary["locales"][locale]
        owner, name = repo["name"].split("/", 1)
        anchor = f"project-{index}-" + re.sub(r"[^a-z0-9-]", "-", repo["name"].lower())
        language = repo["language"] or text["unknown"]
        warning = (
            f'<p class="source-warning">{escape(COPY[locale][summary["status"]])}</p>'
            if summary["status"] != "curated"
            else ""
        )
        highlights = "".join(f"<li>{escape(item)}</li>" for item in note["highlights"])
        purpose = (
            f'<p class="section-label">{text["purpose"]}</p>'
            f'<p class="purpose">{escape(note["purpose"])}</p>'
            if note["purpose"]
            else ""
        )
        feature_section = (
            f'<div class="highlights"><h3>{text["highlights"]}</h3><ul>{highlights}</ul></div>'
            if highlights
            else ""
        )
        daily = f"{number(repo['stars_today'], '+')} {text['today']}"
        cards.append(f'''
<article class="project" id="{anchor}" data-language="{escape(language, quote=True)}">
  <header class="project-heading">
    <span class="project-number" aria-hidden="true">{index:02}</span>
    <div class="project-title"><p class="owner">{escape(owner)}</p>
      <h2><a href="{safe_url(repo["url"])}" target="_blank"
        rel="noopener noreferrer">{escape(name)}{ARROW}</a></h2></div>
    <span class="technology">{escape(language)}</span>
  </header>
  <div class="project-body">{warning}{purpose}{feature_section}
    <footer class="project-footer">
      <a class="source-link" href="{safe_url(repo["readme"]["url"])}" target="_blank"
        rel="noopener noreferrer">{text["source"]} {ARROW}</a>
      <div class="project-metrics"><span>{STAR}{number(repo["stars"])}</span>
        <span class="daily-stars">{daily}</span></div>
    </footer>
  </div>
</article>''')
        contents.append(
            f'<li data-project="{anchor}"><a href="#{anchor}">'
            f"<span>{index:02}</span>{escape(name)}</a></li>"
        )
        jumps.append(f'<option value="{anchor}">{escape(repo["name"])}</option>')
    technologies = sorted({repo["language"] or text["unknown"] for repo in repos})
    options = "".join(
        f'<option value="{escape(language, quote=True)}">{escape(language)}</option>'
        for language in technologies
    )
    total = len(repos)
    count = text["count"].format(visible=total, total=total)
    content = f'''
<section class="reading-tools" aria-label="{text["search_label"]}">
  <label class="search-field"><svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>
    <input id="search" type="search" aria-label="{text["search_label"]}"
      placeholder="{text["search"]}" autocomplete="off"></label>
  <label class="filter-field"><span class="sr-only">{text["filter"]}</span>
    <select id="technology"><option value="">{text["all"]}</option>{options}</select></label>
  <button class="text-button" id="reset" hidden>{text["reset"]}</button>
</section>
<div class="reading-meta"><p id="result-count" role="status"
  data-template="{escape(text["count"], quote=True)}">{count}</p>
  <label class="mobile-jump"><span class="sr-only">{text["jump"]}</span>
    <select id="jump"><option value="">{text["jump"]}</option>
      {"".join(jumps)}</select></label></div>
<div class="reading-layout">
  <aside class="sidebar"><nav class="contents" aria-label="{text["contents"]}">
    <p class="eyebrow">{text["contents"]}</p><ol>{"".join(contents)}</ol></nav>
    <div class="source-note"><span class="note-mark" aria-hidden="true">↳</span>
      <p class="eyebrow">{text["source_note"]}</p>
      <p>{text["source_description"]}</p></div></aside>
  <div class="projects" id="projects">{"".join(cards)}
    <div id="empty-state" class="empty-state" hidden>
      <h2>{text["empty"]}</h2><p>{text["empty_hint"]}</p></div>
  </div>
</div>'''
    words = sum(
        len(note["purpose"].split()) + sum(len(item.split()) for item in note["highlights"])
        for repo in repos
        for note in [repo["summary"]["locales"][locale]]
    )
    characters = sum(
        len(repo["summary"]["locales"][locale]["purpose"])
        + sum(map(len, repo["summary"]["locales"][locale]["highlights"]))
        for repo in repos
    )
    minutes = max(1, math.ceil(characters / 450 if locale == "zh-CN" else words / 230))
    stats = "".join(
        f"<div><strong>{value}</strong><span>{label}</span></div>"
        for value, label in [
            (total, text["projects"]),
            (minutes, text["minutes"]),
            (len({repo["language"] for repo in repos if repo["language"]}), text["languages"]),
        ]
    )
    return document(
        snapshot,
        locale,
        stem="index" if latest else snapshot["date"],
        prefix="" if latest else "../../",
        content=content,
        title=text["title"],
        intro=text["intro"],
        page_kind="issue",
        stats=stats,
    )


def render_html_archive(snapshot: dict, locale: str, days: list[str]) -> str:
    text = TEXT[locale]
    rows = []
    for day in days:
        url = f"{day[:4]}/{day[5:7]}/{html_name(day, locale, 'en')}"
        rows.append(
            f'<a class="archive-issue" href="{url}"><div><span class="eyebrow">'
            f"{text['issue']}</span><h2>{day}</h2></div><span>{text['read']} {ARROW}</span></a>"
        )
    content = (
        f'<section id="projects" class="archive-list" aria-label="{text["archive_label"]}">'
        f"{''.join(rows)}</section>"
    )
    return document(
        snapshot,
        locale,
        stem="archive",
        prefix="",
        content=content,
        title=text["archive_title"],
        intro=text["archive_intro"],
        page_kind="archive",
        stats="",
    )


def html_outputs(root: Path, snapshot: dict) -> dict[Path, str]:
    outputs = {}
    reports = root / "reports"
    day = snapshot["date"]
    locale = snapshot["active_language"]
    dated = reports / day[:4] / day[5:7] / html_name(day, locale, "en")
    outputs[dated] = render_html(snapshot, locale)
    outputs[reports / "index.html"] = render_html(snapshot, locale, latest=True)
    suffix = "" if locale == "en" else "." + locale
    prior = reports.glob(f"????/??/????-??-??{suffix}.html")
    days = sorted({day, *(path.name[:10] for path in prior)}, reverse=True)
    outputs[reports / "archive.html"] = render_html_archive(snapshot, locale, days)
    return outputs
