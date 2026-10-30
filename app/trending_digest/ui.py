"""A compact local configuration and report workspace."""

from __future__ import annotations

import argparse
import copy
import html
import logging
import os
import shutil
import subprocess
import time
import webbrowser
from importlib.resources import files
from pathlib import Path

import gradio as gr
import yaml

from .config import load_config, validate_config
from .lifecycle import BrowserLifecycle
from .matching import selected_repositories
from .service import list_profiles, load_profile, run_generation, save_configuration

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
logger = logging.getLogger(__name__)

TEXT = {
    "en": {
        "title": "Your daily open-source brief",
        "subtitle": "Describe your work, then generate a report.",
        "active_language": "Language / 语言",
        "work_requirements": "Description",
        "work_hint": "Optional. Leave empty to include all projects.",
        "generate": "Generate",
        "save": "Save config",
        "load": "Load config",
        "profile_name": "Configuration name (optional)",
        "profile_name_hint": "Leave empty to save conf.yaml.",
        "profile": "Configuration",
        "confirm_save": "Save",
        "confirm_load": "Load",
        "cancel": "Cancel",
        "saved": "Configuration saved.",
        "profile_saved": "Saved configuration: {name}.",
        "profile_loaded": "Loaded configuration: {name}.",
        "changed": "Language updated.",
        "done": "Report ready · {count} projects · {date}. Opened in your browser.",
        "open_failed": "Report saved to {path}. Open this file in your browser.",
        "error": "Could not complete the operation",
        "ready": "Ready to generate.",
        "popup_success": "Done",
        "popup_error": "Something went wrong",
        "popup_info": "Report saved",
        "popup_close": "OK",
        "loading_generate": "Generating your report",
        "loading_generate_hint": "Fetching repositories and preparing briefs. Please wait.",
        "loading_save": "Saving configuration",
        "loading_save_hint": "Saving your settings. Please wait.",
        "loading_load": "Loading configuration",
        "loading_load_hint": "Restoring the selected settings. Please wait.",
        "connection_error": "Server connection interrupted. Please check the workspace and retry.",
        "unexpected_error": "An unexpected error occurred. Check the terminal log and retry.",
    },
    "zh-CN": {
        "title": "每日开源快报",
        "subtitle": "描述你的工作，一键生成相关项目报告。",
        "active_language": "Language / 语言",
        "work_requirements": "工作描述",
        "work_hint": "可选，留空查看全部项目。",
        "generate": "生成报告",
        "save": "保存配置",
        "load": "加载配置",
        "profile_name": "配置名称（可选）",
        "profile_name_hint": "留空保存当前 conf.yaml。",
        "profile": "选择配置",
        "confirm_save": "保存",
        "confirm_load": "加载",
        "cancel": "取消",
        "saved": "配置已保存。",
        "profile_saved": "已保存配置：{name}。",
        "profile_loaded": "已加载配置：{name}。",
        "changed": "语言已切换。",
        "done": "报告已生成 · {count} 个项目 · {date}，已在浏览器中打开。",
        "open_failed": "报告已保存到 {path}，可在浏览器中打开此文件。",
        "error": "操作未完成",
        "ready": "已就绪，可以生成报告。",
        "popup_success": "操作成功",
        "popup_error": "操作未完成",
        "popup_info": "报告已保存",
        "popup_close": "知道了",
        "loading_generate": "正在生成报告",
        "loading_generate_hint": "正在获取仓库并调用模型整理简报，请稍候。",
        "loading_save": "正在保存配置",
        "loading_save_hint": "正在保存你的设置，请稍候。",
        "loading_load": "正在加载配置",
        "loading_load_hint": "正在恢复所选配置，请稍候。",
        "connection_error": "与服务的连接已中断，请检查工作台后重试。",
        "unexpected_error": "遇到意外错误，请查看启动终端中的记录后重试。",
    },
}


def feedback_payload(locale: str, kind: str, message: str) -> dict:
    copy = TEXT[locale]
    return {
        "kind": kind,
        "title": copy[f"popup_{kind}"],
        "message": message,
        "close": copy["popup_close"],
        "id": str(time.time_ns()),
    }


def error_feedback(locale: str, exc: Exception) -> dict:
    if isinstance(exc, (ValueError, OSError, KeyError, TypeError, yaml.YAMLError)):
        message = str(exc)
    else:
        logger.exception("Unexpected workspace operation failure")
        message = TEXT[locale]["unexpected_error"]
    return feedback_payload(locale, "error", message)


def feedback_loading_js(operation: str) -> str:
    return (
        "(...args) => { window.trendingFeedback?.loading(args[1], "
        + repr(operation)
        + "); return args; }"
    )


def edited_config(base: dict, locale: str, description: str) -> dict:
    checked = copy.deepcopy(base)
    checked["active_language"] = locale
    checked["work_requirements"] = {"description": description}
    return validate_config(checked)


def hero(locale: str) -> str:
    text = TEXT[locale]
    return (
        '<div class="desk-hero"><span class="desk-kicker">TRENDING BRIEF</span>'
        f"<h1>{text['title']}</h1><p>{text['subtitle']}</p></div>"
    )


def open_report(root: Path) -> bool:
    path = root / "output/reports/index.html"
    if not path.is_file():
        raise FileNotFoundError("The generated HTML report is missing")
    try:
        return webbrowser.open_new_tab(path.resolve().as_uri())
    except (OSError, webbrowser.Error):
        return False


def create_ui(root: Path, lifecycle: BrowserLifecycle | None = None) -> gr.Blocks:
    config = load_config(root / "conf.yaml")
    locale = config["active_language"]
    text = TEXT[locale]

    def choices():
        return [("conf.yaml", ""), *((name, name) for name in list_profiles(root))]

    with gr.Blocks(title="Trending Brief", fill_width=True, analytics_enabled=False) as app:
        config_state = gr.State(config)
        selected_profile = gr.State("")
        with gr.Row(elem_id="workspace-header"):
            with gr.Column(scale=4, min_width=240):
                heading = gr.HTML(hero(locale))
            with gr.Column(scale=1, min_width=170):
                language = gr.Dropdown(
                    choices=[("English", "en"), ("简体中文", "zh-CN")],
                    value=locale,
                    label=text["active_language"],
                    elem_id="active-language",
                    interactive=True,
                )
        with gr.Column(elem_id="main-settings"):
            requirements = gr.Textbox(
                value=config["work_requirements"]["description"],
                label=text["work_requirements"],
                info=text["work_hint"],
                lines=4,
                max_lines=8,
                elem_id="work-requirements",
            )
            with gr.Row(elem_id="action-row"):
                save = gr.Button(text["save"], min_width=110, scale=1, elem_id="save-config")
                load = gr.Button(text["load"], min_width=110, scale=1, elem_id="load-config")
                generate = gr.Button(
                    text["generate"],
                    variant="primary",
                    min_width=150,
                    scale=2,
                    elem_id="generate-report",
                )
            with gr.Group(visible=False, elem_id="save-config-panel") as save_panel:
                profile_name = gr.Textbox(
                    label=text["profile_name"],
                    info=text["profile_name_hint"],
                    elem_id="profile-name",
                )
                with gr.Row():
                    confirm_save = gr.Button(text["confirm_save"], variant="primary")
                    cancel_save = gr.Button(text["cancel"])
            with gr.Group(visible=False, elem_id="load-config-panel") as load_panel:
                profile = gr.Dropdown(
                    choices=choices(),
                    value="",
                    label=text["profile"],
                    interactive=True,
                    elem_id="saved-profile",
                )
                with gr.Row():
                    confirm_load = gr.Button(text["confirm_load"], variant="primary")
                    cancel_load = gr.Button(text["cancel"])
            status = gr.Markdown(text["ready"], elem_id="operation-status")
        resources = files("trending_digest").joinpath("templates")
        labels = {
            locale: {
                **{
                    operation: {
                        "title": copy[f"loading_{operation}"],
                        "message": copy[f"loading_{operation}_hint"],
                    }
                    for operation in ("generate", "save", "load")
                },
                "error": copy["popup_error"],
                "connection": copy["connection_error"],
                "close": copy["popup_close"],
            }
            for locale, copy in TEXT.items()
        }
        feedback = gr.HTML(
            {"kind": "idle", "labels": labels},
            html_template=resources.joinpath("feedback.html").read_text(encoding="utf-8"),
            js_on_load=resources.joinpath("feedback.js").read_text(encoding="utf-8"),
            elem_id="operation-feedback",
            min_height=0,
            padding=False,
        )

        translated = [
            heading,
            language,
            requirements,
            save,
            load,
            generate,
            status,
            profile_name,
            profile,
            confirm_save,
            confirm_load,
            cancel_save,
            cancel_load,
        ]

        def translate(locale, *, checked=None, message=None):
            copy = TEXT[locale]
            language_params = {"label": copy["active_language"]}
            description_params = {"label": copy["work_requirements"], "info": copy["work_hint"]}
            if checked:
                language_params["value"] = checked["active_language"]
                description_params["value"] = checked["work_requirements"]["description"]
            return {
                heading: gr.update(value=hero(locale)),
                language: gr.update(**language_params),
                requirements: gr.update(**description_params),
                save: gr.update(value=copy["save"]),
                load: gr.update(value=copy["load"]),
                generate: gr.update(value=copy["generate"]),
                status: message or copy["changed"],
                profile_name: gr.update(label=copy["profile_name"], info=copy["profile_name_hint"]),
                profile: gr.update(label=copy["profile"], choices=choices()),
                confirm_save: gr.update(value=copy["confirm_save"]),
                confirm_load: gr.update(value=copy["confirm_load"]),
                cancel_save: gr.update(value=copy["cancel"]),
                cancel_load: gr.update(value=copy["cancel"]),
            }

        def localize(locale):
            return translate(locale)

        def restore(request: gr.Request):
            if lifecycle:
                lifecycle.connect(request.session_hash)
            try:
                checked = load_config(root / "conf.yaml")
                return {
                    **translate(
                        checked["active_language"],
                        checked=checked,
                        message=TEXT[checked["active_language"]]["ready"],
                    ),
                    config_state: checked,
                }
            except Exception as exc:
                return {feedback: error_feedback(locale, exc), status: TEXT[locale]["error"]}

        def show_save(name):
            return gr.update(visible=True), gr.update(visible=False), gr.update(value=name)

        def show_load(name, locale):
            try:
                available = list_profiles(root)
                return {
                    save_panel: gr.update(visible=False),
                    load_panel: gr.update(visible=True),
                    profile: gr.update(choices=choices(), value=name if name in available else ""),
                }
            except Exception as exc:
                return {feedback: error_feedback(locale, exc)}

        def save_form(base, locale, description, name):
            try:
                checked = edited_config(base, locale, description)
                name = name.strip()
                save_configuration(root, checked, profile_name=name or None)
                message = (
                    TEXT[locale]["profile_saved"].format(name=html.escape(name))
                    if name
                    else TEXT[locale]["saved"]
                )
                return (
                    checked,
                    name,
                    message,
                    gr.update(visible=False),
                    feedback_payload(locale, "success", message),
                )
            except Exception as exc:
                return (
                    gr.skip(),
                    gr.skip(),
                    TEXT[locale]["error"],
                    gr.update(visible=True),
                    error_feedback(locale, exc),
                )

        def load_form(name, locale):
            try:
                checked = load_profile(root, name) if name else load_config(root / "conf.yaml")
                result = translate(
                    checked["active_language"],
                    checked=checked,
                    message=TEXT[checked["active_language"]]["profile_loaded"].format(
                        name=html.escape(name or "conf.yaml"),
                    ),
                )
                result.update(
                    {
                        config_state: checked,
                        selected_profile: name,
                        save_panel: gr.update(visible=False),
                        load_panel: gr.update(visible=False),
                    }
                )
                result[profile] = gr.update(
                    choices=choices(), value=name, label=TEXT[checked["active_language"]]["profile"]
                )
                result[feedback] = feedback_payload(
                    checked["active_language"],
                    "success",
                    TEXT[checked["active_language"]]["profile_loaded"].format(
                        name=name or "conf.yaml"
                    ),
                )
                return result
            except Exception as exc:
                return {feedback: error_feedback(locale, exc), status: TEXT[locale]["error"]}

        def generate_form(base, locale, description):
            try:
                checked = edited_config(base, locale, description)
                snapshot = run_generation(root, checked)
                opened = open_report(root)
                message = (
                    TEXT[locale]["done"].format(
                        date=snapshot["date"],
                        count=len(selected_repositories(snapshot)),
                    )
                    if opened
                    else TEXT[locale]["open_failed"].format(
                        path=html.escape(str(root / "output/reports/index.html")),
                    )
                )
                return (
                    checked,
                    message,
                    gr.update(visible=False),
                    gr.update(visible=False),
                    feedback_payload(locale, "success" if opened else "info", message),
                )
            except Exception as exc:
                return (
                    gr.skip(),
                    TEXT[locale]["error"],
                    gr.update(visible=False),
                    gr.update(visible=False),
                    error_feedback(locale, exc),
                )

        language.input(
            localize,
            inputs=language,
            outputs=translated,
            queue=False,
            show_progress="hidden",
            js="(language) => { document.documentElement.lang = language; return language; }",
        )
        app.load(
            restore,
            outputs=[*translated, config_state, feedback],
            queue=False,
            show_progress="hidden",
        ).then(
            fn=None,
            inputs=language,
            outputs=None,
            js="(language) => { document.documentElement.lang = language; }",
        )
        save.click(
            show_save,
            inputs=selected_profile,
            outputs=[save_panel, load_panel, profile_name],
            queue=False,
            show_progress="hidden",
        )
        load.click(
            show_load,
            inputs=[selected_profile, language],
            outputs=[save_panel, load_panel, profile, feedback],
            queue=False,
            show_progress="hidden",
        )
        cancel_save.click(lambda: gr.update(visible=False), outputs=save_panel, queue=False)
        cancel_load.click(lambda: gr.update(visible=False), outputs=load_panel, queue=False)
        confirm_save.click(
            save_form,
            inputs=[config_state, language, requirements, profile_name],
            outputs=[config_state, selected_profile, status, save_panel, feedback],
            concurrency_id="workspace",
            show_progress="hidden",
            js=feedback_loading_js("save"),
        ).failure(
            fn=None,
            inputs=language,
            outputs=None,
            js="locale => { window.trendingFeedback?.failed(locale); }",
        )
        confirm_load.click(
            load_form,
            inputs=[profile, language],
            outputs=[*translated, config_state, selected_profile, save_panel, load_panel, feedback],
            concurrency_id="workspace",
            show_progress="hidden",
            js=feedback_loading_js("load"),
        ).failure(
            fn=None,
            inputs=language,
            outputs=None,
            js="locale => { window.trendingFeedback?.failed(locale); }",
        ).then(
            fn=None,
            inputs=language,
            outputs=None,
            js="(language) => { document.documentElement.lang = language; }",
        )
        generate.click(
            generate_form,
            inputs=[config_state, language, requirements],
            outputs=[config_state, status, save_panel, load_panel, feedback],
            concurrency_id="workspace",
            show_progress="hidden",
            js=feedback_loading_js("generate"),
            trigger_mode="once",
        ).failure(
            fn=None,
            inputs=language,
            outputs=None,
            js="locale => { window.trendingFeedback?.failed(locale); }",
        )
        if lifecycle:

            def connected(request: gr.Request):
                lifecycle.connect(request.session_hash)

            def disconnected(request: gr.Request):
                lifecycle.disconnect(request.session_hash)

            # Gradio's persistent heartbeat detects closed tabs; the timer repairs reconnects.
            gr.Timer(3).tick(connected, queue=False, api_visibility="private")
            app.unload(disconnected)
    return app.queue(default_concurrency_limit=1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trending Brief local configuration workspace")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--port",
        type=int,
        help="Use a fixed port; by default, automatically try available ports starting at 7860",
    )
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Keep the server running after workspace tabs are closed",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not os.environ.get("GITHUB_TOKEN"):
        token = os.environ.get("GH_TOKEN")
        gh = shutil.which("gh")
        portable = root.parent / ".tools/gh/gh.exe"
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
    lifecycle = None if args.keep_alive else BrowserLifecycle()
    app = create_ui(root, lifecycle=lifecycle)
    css = files("trending_digest").joinpath("templates/ui.css").read_text(encoding="utf-8")
    app.launch(
        server_name="127.0.0.1",
        server_port=args.port,
        inbrowser=not args.no_browser,
        allowed_paths=[str(root / "output/reports")],
        css=css,
        theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="stone"),
        footer_links=[],
        share=False,
        prevent_thread_lock=True,
    )
    try:
        while lifecycle is None or not lifecycle.should_stop():
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        app.close()


if __name__ == "__main__":
    main()
