"""Local Gradio configuration editor and report workspace."""

from __future__ import annotations

import argparse
import html
import os
import shutil
import subprocess
from importlib.resources import files
from pathlib import Path

import gradio as gr
import yaml
from bs4 import BeautifulSoup

from .config import load_config, validate_config
from .service import run_generation, save_configuration

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

FIELDS = [
    "active_language",
    "programming_language",
    "spoken_language",
    "top_n",
    "timezone",
    "max_chars",
    "timeout_seconds",
    "workers",
    "mode",
    "curated_file",
    "fallback",
    "highlights",
]
TEXT = {
    "en": {
        "title": "Your daily open-source reading desk.",
        "subtitle": "Tune the source, choose a language, "
        "and turn project READMEs into a readable brief.",
        "general": "### Reading & discovery",
        "fetch": "### README & summaries",
        "active_language": "Interface & report language",
        "programming_language": "Programming-language filter",
        "spoken_language": "Project description-language filter",
        "top_n": "Projects per issue",
        "timezone": "Issue timezone",
        "max_chars": "README excerpt input limit (characters)",
        "timeout_seconds": "Request timeout (seconds)",
        "workers": "Parallel README requests",
        "mode": "Summary strategy",
        "curated_file": "Saved summary file",
        "fallback": "Fallback for new or changed READMEs",
        "highlights": "Highlights per project",
        "curated": "Prefer saved summaries",
        "extractive": "Source excerpts",
        "save": "Save configuration",
        "generate": "Fetch & generate report",
        "cached": "Generate from saved data",
        "preview": "### Report preview",
        "download": "Download HTML report",
        "ready": "Ready. Changes are saved when you click Save or Generate.",
        "changed": "Interface language updated. Save or Generate to keep this choice in conf.yaml.",
        "saved": "Configuration saved. Future runs will generate only {language} reports.",
        "done": "Report ready · {date} · {count} projects · {language}.",
        "cached_done": "Report rendered from saved data · {date} · {count} projects · {language}. "
        "No new fetch.",
        "no_preview": "Generate a report in the selected language to preview it here.",
        "hint": "Leave source filters empty for all projects. Saved-data generation reuses "
        "the original capture and does not apply new source filters.",
        "error": "Could not complete the operation",
        "language_en": "English",
        "language_zh": "Simplified Chinese",
    },
    "zh-CN": {
        "title": "你的每日开源阅读工作台。",
        "subtitle": "调整抓取来源，选择阅读语言，把项目 README 整理成易读的技术快报。",
        "general": "### 阅读与项目发现",
        "fetch": "### README 与摘要",
        "active_language": "界面与报告语言",
        "programming_language": "编程语言筛选",
        "spoken_language": "项目描述语言筛选",
        "top_n": "每期项目数量",
        "timezone": "快报时区",
        "max_chars": "README 摘录输入上限（字符）",
        "timeout_seconds": "请求超时（秒）",
        "workers": "README 抓取并发数",
        "mode": "摘要策略",
        "curated_file": "已整理摘要文件",
        "fallback": "新增或有变化的 README 如何处理",
        "highlights": "每个项目的亮点数量",
        "curated": "优先使用已整理摘要",
        "extractive": "来源原文摘录",
        "save": "保存配置",
        "generate": "抓取并生成报告",
        "cached": "用已保存数据生成",
        "preview": "### 报告预览",
        "download": "下载 HTML 报告",
        "ready": "已就绪。点击保存或生成时，才会将修改写入配置。",
        "changed": "界面语言已切换。点击保存或生成后，此选择会写入 conf.yaml。",
        "saved": "配置已保存，后续运行只生成{language}报告。",
        "done": "报告已生成 · {date} · {count} 个项目 · {language}。",
        "cached_done": "已使用保存的数据生成 · {date} · {count} 个项目 · {language}。未重新抓取。",
        "no_preview": "生成当前所选语言的报告后，可在此预览。",
        "hint": "来源筛选留空表示全部项目。使用已保存数据时沿用原采集结果，不应用新的来源筛选。",
        "error": "操作未完成",
        "language_en": "英文",
        "language_zh": "中文",
    },
}


def form_values(config: dict) -> list:
    return [
        config[key] if key in config else config["readme"].get(key, config["summary"].get(key))
        for key in FIELDS
    ]


def config_from_values(values: list) -> dict:
    fields = dict(zip(FIELDS, values, strict=True))
    for key in ("top_n", "max_chars", "timeout_seconds", "workers", "highlights"):
        number = fields[key]
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or int(number) != number
        ):
            raise ValueError(f"{key} must be an integer")
        fields[key] = int(number)
    return validate_config(
        {
            **{key: fields[key] for key in FIELDS[:5]},
            "readme": {key: fields[key] for key in FIELDS[5:8]},
            "summary": {key: fields[key] for key in FIELDS[8:]},
        }
    )


def hero(locale: str) -> str:
    text = TEXT[locale]
    return (
        f'<div class="desk-hero"><span class="desk-kicker">TRENDING BRIEF / STUDIO</span>'
        f"<h1>{text['title']}</h1><p>{text['subtitle']}</p></div>"
    )


def report_preview(root: Path, locale: str) -> tuple[str, str | None]:
    path = root / "reports/index.html"
    if path.exists():
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        if soup.html and soup.html.get("lang") == locale:
            # The embedded preview has no filesystem context. Downloads retain full navigation.
            for navigation in soup.select(".primary-nav, .locale-switch"):
                navigation.decompose()
            for link in soup.select(".wordmark, .footer-brand"):
                link["href"] = "#top"
            content = html.escape(str(soup), quote=True)
            return (
                f'<iframe class="report-frame" title="{TEXT[locale]["download"]}" '
                'sandbox="allow-scripts allow-modals allow-popups '
                'allow-popups-to-escape-sandbox" '
                f'srcdoc="{content}"></iframe>',
                str(path),
            )
    return f'<div class="preview-empty">{TEXT[locale]["no_preview"]}</div>', None


def create_ui(root: Path) -> gr.Blocks:
    config = load_config(root / "conf.yaml")
    locale = config["active_language"]
    text = TEXT[locale]
    initial = dict(zip(FIELDS, form_values(config), strict=True))
    with gr.Blocks(title="Trending Brief Studio", fill_width=True, analytics_enabled=False) as app:
        heading = gr.HTML(hero(locale))
        with gr.Row(elem_id="settings-layout", equal_height=True):
            with gr.Column(min_width=260, scale=1, elem_id="discovery-panel"):
                general_title = gr.Markdown(text["general"])
                language = gr.Dropdown(
                    choices=[("English", "en"), ("简体中文", "zh-CN")],
                    value=locale,
                    label=text["active_language"],
                    elem_id="active-language",
                )
                with gr.Row():
                    programming = gr.Textbox(
                        value=initial["programming_language"],
                        label=text["programming_language"],
                        placeholder="python, rust, c++…",
                        min_width=120,
                    )
                    spoken = gr.Textbox(
                        value=initial["spoken_language"],
                        label=text["spoken_language"],
                        placeholder="zh, en…",
                        min_width=120,
                    )
                top = gr.Slider(1, 25, value=config["top_n"], step=1, label=text["top_n"])
                timezone = gr.Textbox(
                    value=config["timezone"], label=text["timezone"], placeholder="Asia/Shanghai"
                )
                hint = gr.Markdown(text["hint"], elem_id="settings-hint")
            with gr.Column(min_width=260, scale=1, elem_id="summary-panel"):
                fetch_title = gr.Markdown(text["fetch"])
                with gr.Row():
                    timeout = gr.Number(
                        value=initial["timeout_seconds"],
                        precision=0,
                        label=text["timeout_seconds"],
                        minimum=1,
                        maximum=120,
                        min_width=120,
                    )
                    workers = gr.Number(
                        value=initial["workers"],
                        precision=0,
                        label=text["workers"],
                        minimum=1,
                        maximum=8,
                        min_width=120,
                    )
                maximum = gr.Number(
                    value=initial["max_chars"],
                    precision=0,
                    label=text["max_chars"],
                    minimum=1000,
                    maximum=100000,
                )
                with gr.Row():
                    mode = gr.Dropdown(
                        choices=[(text["curated"], "curated"), (text["extractive"], "extractive")],
                        value=initial["mode"],
                        label=text["mode"],
                        min_width=120,
                    )
                    highlights = gr.Slider(
                        1,
                        5,
                        value=initial["highlights"],
                        step=1,
                        label=text["highlights"],
                        min_width=120,
                    )
                curated = gr.Textbox(value=initial["curated_file"], label=text["curated_file"])
                fallback = gr.Dropdown(
                    choices=[(text["extractive"], "extractive")],
                    value="extractive",
                    label=text["fallback"],
                    interactive=False,
                )
        with gr.Row(elem_id="action-row"):
            save = gr.Button(text["save"], variant="secondary", min_width=140)
            cached = gr.Button(text["cached"], variant="secondary", min_width=140)
            generate = gr.Button(text["generate"], variant="primary", min_width=160)
        status = gr.Markdown(text["ready"], elem_id="operation-status")
        preview_title = gr.Markdown(text["preview"])
        preview_html, report_file = report_preview(root, locale)
        preview = gr.HTML(preview_html, elem_id="report-preview")
        download = gr.File(value=report_file, label=text["download"], interactive=False)

        widgets = dict(
            zip(
                FIELDS,
                [
                    language,
                    programming,
                    spoken,
                    top,
                    timezone,
                    maximum,
                    timeout,
                    workers,
                    mode,
                    curated,
                    fallback,
                    highlights,
                ],
                strict=True,
            )
        )
        inputs = [widgets[key] for key in FIELDS]
        translated = [
            heading,
            general_title,
            fetch_title,
            hint,
            *inputs,
            save,
            cached,
            generate,
            status,
            preview_title,
            preview,
            download,
        ]

        def localize(selected):
            copy = TEXT[selected]
            updates = [
                gr.update(value=hero(selected)),
                gr.update(value=copy["general"]),
                gr.update(value=copy["fetch"]),
                gr.update(value=copy["hint"]),
            ]
            for key in FIELDS:
                params = {"label": copy[key]}
                if key == "mode":
                    params["choices"] = [
                        (copy["curated"], "curated"),
                        (copy["extractive"], "extractive"),
                    ]
                if key == "fallback":
                    params["choices"] = [(copy["extractive"], "extractive")]
                updates.append(gr.update(**params))
            content, filename = report_preview(root, selected)
            return [
                *updates,
                gr.update(value=copy["save"]),
                gr.update(value=copy["cached"]),
                gr.update(value=copy["generate"]),
                copy["changed"],
                copy["preview"],
                content,
                gr.update(value=filename, label=copy["download"]),
            ]

        def save_form(*values):
            selected = values[0]
            try:
                checked = save_configuration(root, config_from_values(list(values)))
                label = TEXT[selected][
                    "language_en" if checked["active_language"] == "en" else "language_zh"
                ]
                return TEXT[selected]["saved"].format(language=label)
            except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as exc:
                raise gr.Error(f"{TEXT[selected]['error']}: {exc}") from exc

        def generate_form(*values, use_saved=False):
            selected = values[0]
            try:
                snapshot = run_generation(root, config_from_values(list(values)), cached=use_saved)
                content, filename = report_preview(root, selected)
                label = TEXT[selected]["language_en" if selected == "en" else "language_zh"]
                message = TEXT[selected]["cached_done" if use_saved else "done"].format(
                    date=snapshot["date"],
                    count=min(snapshot["top_n"], len(snapshot["repositories"])),
                    language=label,
                )
                return message, content, filename
            except (ValueError, OSError, KeyError, yaml.YAMLError) as exc:
                raise gr.Error(f"{TEXT[selected]['error']}: {exc}") from exc

        def restore():
            checked = load_config(root / "conf.yaml")
            selected = checked["active_language"]
            updates = localize(selected)
            for index, value in enumerate(form_values(checked)):
                updates[4 + index]["value"] = value
            updates[4 + len(FIELDS) + 3] = TEXT[selected]["ready"]
            return updates

        language.input(
            localize,
            inputs=language,
            outputs=translated,
            queue=False,
            js="(language) => { document.documentElement.lang = language; return language; }",
        )
        app.load(restore, outputs=translated, queue=False).then(
            fn=None,
            inputs=language,
            outputs=None,
            js="(language) => { document.documentElement.lang = language; }",
        )
        save.click(save_form, inputs=inputs, outputs=status, concurrency_id="workspace")
        generate.click(
            generate_form,
            inputs=inputs,
            outputs=[status, preview, download],
            concurrency_id="workspace",
        )
        cached.click(
            lambda *values: generate_form(*values, use_saved=True),
            inputs=inputs,
            outputs=[status, preview, download],
            concurrency_id="workspace",
        )
    return app.queue(default_concurrency_limit=1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trending Brief local configuration workspace")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not os.environ.get("GITHUB_TOKEN"):
        token = os.environ.get("GH_TOKEN")
        gh = shutil.which("gh")
        portable = Path(__file__).resolve().parents[2] / ".tools/gh/gh.exe"
        if not gh and portable.is_file():
            gh = str(portable)
        if not token and gh:
            try:
                result = subprocess.run(
                    [gh, "auth", "token"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if result.returncode == 0:
                    token = result.stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                pass
        if token:
            os.environ["GITHUB_TOKEN"] = token
    app = create_ui(root)
    css = files("trending_digest").joinpath("templates/ui.css").read_text(encoding="utf-8")
    app.launch(
        server_name="127.0.0.1",
        server_port=args.port,
        inbrowser=not args.no_browser,
        allowed_paths=[str(root / "reports")],
        css=css,
        theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="stone"),
        footer_links=[],
        share=False,
    )


if __name__ == "__main__":
    main()
