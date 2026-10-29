"""Chinese editorial structure with source descriptions kept verbatim."""

from __future__ import annotations

import html
import re
from collections import Counter
from pathlib import Path

CATEGORIES = (
    (
        "AI / 模型与智能体",
        r"\b(ai|llm|gpt|agent|agents|transformer|inference|diffusion|rag|ml)\b",
        "关注模型支持、运行资源和数据流向，先用自己的小样本验证效果。",
    ),
    (
        "安全与隐私",
        r"\b(security|privacy|vulnerability|pentest|encryption|hacking|cybersecurity)\b",
        "关注授权范围、威胁模型和维护情况，在隔离环境中评估。",
    ),
    (
        "数据与存储",
        r"\b(database|sql|postgres|redis|analytics|storage|dataframe|vector)\b",
        "关注数据兼容性、查询性能与迁移成本，用代表性数据做验证。",
    ),
    (
        "Web 与应用开发",
        r"\b(web|frontend|react|nextjs|vue|browser|javascript|typescript|css|ui)\b",
        "关注框架兼容性、交互体验和集成成本，适合用小型原型试用。",
    ),
    (
        "基础设施与工程效率",
        r"\b(cli|terminal|devops|docker|kubernetes|workflow|developer|rust|compiler)\b",
        "关注现有工具链兼容性、部署复杂度和团队迁移成本。",
    ),
    (
        "学习与知识资源",
        r"\b(awesome|tutorial|course|learn|learning|interview|collection|roadmap)\b",
        "关注内容更新时间与示例可复现性，可以挑选一个主题实际练习。",
    ),
)


def classify(repo: dict) -> tuple[str, str]:
    text = repo["name"] + " " + repo["description"]
    for category, pattern, tip in CATEGORIES:
        if re.search(pattern, text, re.IGNORECASE):
            return category, tip
    return "其他技术项目", "从 README、许可证和最近提交开始，确认是否适合自己的使用场景。"


def safe_text(text: str) -> str:
    text = html.escape(" ".join(text.split()), quote=False)
    return re.sub(r"([\\`*_{\[\]()|#!])", r"\\\1", text)


def number(value: int | None, prefix: str = "") -> str:
    return "—" if value is None else f"{prefix}{value:,}"


def report_path(day: str) -> str:
    return f"daily/{day[:4]}/{day[5:7]}/{day}.md"


def movement(repo: dict, previous: dict | None) -> str:
    if previous is None:
        return "首次采集，无可比快照"
    old = {r["name"].lower(): r["rank"] for r in previous["repositories"]}
    rank = old.get(repo["name"].lower())
    if rank is None:
        return "新入当前采集榜单"
    delta = rank - repo["rank"]
    return f"↑ {delta}" if delta > 0 else (f"↓ {-delta}" if delta < 0 else "持平")


def render_digest(snapshot: dict, previous: dict | None) -> str:
    repos = snapshot["repositories"]
    selected = repos[: snapshot["top_n"]]
    categories = Counter(classify(repo)[0] for repo in selected)
    languages = Counter(repo["language"] or "未标注" for repo in selected)
    lines = [
        f"# GitHub 技术快报 · {snapshot['date']}",
        "",
        f"> 采集时间：{snapshot['fetched_at']}（{snapshot['timezone']}）",
        ">",
        f"> 数据来源：[GitHub Trending · Daily]({snapshot['source_url']})",
        ">",
        f"> 收录 {len(repos)} 个项目，重点阅读前 {len(selected)} 个。",
        "",
        "## 今日速览",
        "",
        "- **技术方向**：" + "、".join(f"{k} {v} 个" for k, v in categories.most_common()) + "。",
        "- **主要语言**："
        + "、".join(f"{safe_text(k)} {v} 个" for k, v in languages.most_common(4))
        + "。",
    ]
    known = [r for r in repos if r["stars_today"] is not None]
    if known:
        fastest = max(known, key=lambda r: r["stars_today"])
        lines.append(
            f"- **榜内日增 Star 最多**：[{fastest['name']}]({fastest['url']})，"
            f"页面标注 {number(fastest['stars_today'], '+')}。"
        )
    if previous:
        old_names = {r["name"].lower() for r in previous["repositories"]}
        newcomers = sum(r["name"].lower() not in old_names for r in repos)
        lines.append(
            f"- **榜单变化**：相比 {previous['date']} 的同源快照，"
            f"当前榜单有 {newcomers} 个新出现项目。"
        )
    else:
        lines.append("- **榜单变化**：首次采集，下一期起对比此前最近一次同源快照。")
    lines.extend(["", "## 重点项目", ""])
    for repo in selected:
        category, tip = classify(repo)
        lines.extend(
            [
                f"### {repo['rank']}. [{repo['name']}]({repo['url']})",
                "",
                f"**方向线索**：{category} · **语言**：{safe_text(repo['language'] or '未标注')}",
                "",
                f"**Star**：{number(repo['stars'])}"
                f" · **今日新增**：{number(repo['stars_today'], '+')}"
                f" · **Fork**：{number(repo['forks'])} · **排名变化**：{movement(repo, previous)}",
                "",
                "**项目说明（原文）**：" + safe_text(repo["description"] or "页面未提供项目说明。"),
                "",
                f"**试用关注点**：{tip}",
                "",
            ]
        )
    lines.extend(
        [
            "## 完整榜单",
            "",
            "| 排名 | 项目 | 语言 | Star | 今日新增 | 变化 |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for repo in repos:
        lines.append(
            f"| {repo['rank']} | [{repo['name']}]({repo['url']}) | "
            f"{safe_text(repo['language'] or '—')} | {number(repo['stars'])} | "
            f"{number(repo['stars_today'], '+')} | {movement(repo, previous)} |"
        )
    lines.extend(
        [
            "",
            "## 数据口径",
            "",
            "- 排序沿用采集时的 GitHub Trending 日榜，不按总 Star 重新排序。",
            "- “今日新增”来自页面的 stars today 字段；不是本仓库两次采样的差值。缺失值显示为 —。",
            "- “新入榜”和排名变化以此前最近一次同源快照为准，不代表首次登上 GitHub Trending。",
            "- 技术方向是基于项目名称和描述的关键词归类，试用关注点是通用建议，未经项目实测。",
            "- 项目说明保留来源原文；本快报不调用大模型，不自动编写未经核验的项目能力。",
            "- GitHub Trending 是动态页面，同一天不同采集时间的结果可能不同。",
            "",
        ]
    )
    return "\n".join(lines)


def archive_index(root: Path) -> str:
    paths = sorted((root / "daily").glob("????/??/????-??-??.md"), reverse=True)
    return (
        "# 技术快报归档\n\n"
        + "\n".join(f"- [{p.stem}]({p.relative_to(root / 'daily').as_posix()})" for p in paths)
        + "\n"
    )


def update_readme(readme: str, snapshot: dict) -> str:
    start, end = "<!-- digest:start -->", "<!-- digest:end -->"
    if (
        readme.count(start) != 1
        or readme.count(end) != 1
        or readme.index(start) > readme.index(end)
    ):
        raise ValueError("README must contain exactly one ordered digest marker pair")
    lines = [
        start,
        "",
        f"### {snapshot['date']} · 最新一期",
        "",
        f"[阅读完整快报]({report_path(snapshot['date'])}) · [历史归档](daily/README.md)",
        "",
        "| 排名 | 项目 | 今日新增 Star |",
        "| --- | --- | ---: |",
    ]
    for repo in snapshot["repositories"][:5]:
        lines.append(
            f"| {repo['rank']} | [{repo['name']}]({repo['url']}) | "
            f"{number(repo['stars_today'], '+')} |"
        )
    lines.extend(["", end])
    return readme[: readme.index(start)] + "\n".join(lines) + readme[readme.index(end) + len(end) :]
