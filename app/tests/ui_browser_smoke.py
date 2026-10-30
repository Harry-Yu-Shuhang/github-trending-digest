"""Compact UI browser checks in an isolated, offline workspace."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import urlopen

from model_fixtures import fake_analysis
from playwright.sync_api import expect, sync_playwright

from trending_digest.config import load_config
from trending_digest.service import run_generation

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "app/.cache/ui-browser"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="compact workspace ", dir=OUTPUT)).resolve()
    for name in ("conf.yaml", "README.md", "docs/README.zh-CN.md"):
        (workspace / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, workspace / name)
    (workspace / "summaries.yaml").write_text("schema_version: 1\nprojects: {}\n", encoding="utf-8")
    repos = []
    for name, description, language in [
        ("example/game-profiler", "Unreal Engine GPU performance profiler", "C++"),
        ("example/search", "Search and index local documents", "Python"),
    ]:
        repos.append(
            {
                "name": name,
                "url": f"https://github.com/{name}",
                "description": description,
                "language": language,
                "stars": 100,
                "stars_today": 10,
                "readme": {
                    "sha": "a" * 40,
                    "url": f"https://github.com/{name}#readme",
                    "status": "ok",
                    "excerpt": description,
                },
                "summary": {
                    "status": "extractive",
                    "locales": {
                        locale: {"purpose": description, "highlights": ["Works on local projects."]}
                        for locale in ("en", "zh-CN")
                    },
                },
            }
        )
    snapshot = {
        "schema_version": 3,
        "date": "2026-10-29",
        "fetched_at": "2026-10-29T09:17:00+08:00",
        "source_url": "https://github.com/trending?since=daily",
        "top_n": 25,
        "active_language": "en",
        "repositories": repos,
    }
    snapshot_path = workspace / "output/data/2026/10/2026-10-29.json"
    snapshot_path.parent.mkdir(parents=True)
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    config = load_config(workspace / "conf.yaml")
    config["active_language"] = "en"
    config["top_n"] = 7
    config["programming_language"] = "rust"
    config["readme"]["workers"] = 2
    config["llm"]["model"] = "browser-test-model"
    config["work_requirements"] = {"description": ""}
    with patch("trending_digest.llm.request_analysis", side_effect=fake_analysis):
        run_generation(workspace, config, cached=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    opened = workspace / "opened-report.txt"
    offline_generation = (
        "def generate_offline(root, config, cached=False):\n"
        "    time.sleep(1)\n"
        "    if config['work_requirements']['description'] == 'simulate error':\n"
        "        raise ValueError('Model request failed <img src=x onerror=alert(1)>')\n"
        "    return original(root, config, cached=True)\n"
        "ui.run_generation=generate_offline\n"
    )
    # Supply offline data to the production callback and record the OS-browser request.
    script = (
        "import pathlib, webbrowser, sys, time; import trending_digest.ui as ui; "
        f"sys.path.insert(0, {str(ROOT / 'app/tests')!r}); "
        "from model_fixtures import fake_analysis; import trending_digest.llm as llm; "
        "llm.request_analysis=fake_analysis; "
        f"target=pathlib.Path({str(opened)!r}); "
        "webbrowser.open_new_tab=lambda url: (target.write_text(url, encoding='utf-8') or True); "
        "original=ui.run_generation; "
        f"exec({offline_generation!r}); "
        "ui.main()"
    )
    errors = []
    with (OUTPUT / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                "--root",
                str(workspace),
                "--no-browser",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            env={
                **os.environ,
                "GRADIO_ANALYTICS_ENABLED": "False",
                "PYTHONIOENCODING": "utf-8",
                "GITHUB_TOKEN": "ui-test",
            },
        )
        try:
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError((OUTPUT / "server.log").read_text(encoding="utf-8"))
                try:
                    with urlopen(url, timeout=1):
                        break
                except (URLError, TimeoutError):
                    time.sleep(0.25)
            else:
                raise TimeoutError("UI server did not start")
            with sync_playwright() as playwright:
                candidates = [
                    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
                ]
                executable = next((str(path) for path in candidates if path.exists()), None)
                browser = playwright.chromium.launch(headless=True, executable_path=executable)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url)
                dialog = page.locator("#operation-dialog")

                def dismiss_feedback():
                    expect(dialog).to_have_attribute("data-kind", "success")
                    dialog.locator("[data-dismiss]").click()
                    expect(dialog).not_to_be_visible()

                def assert_dialog_centered():
                    box = dialog.bounding_box()
                    viewport = page.viewport_size
                    assert box and viewport
                    assert abs(box["x"] + box["width"] / 2 - viewport["width"] / 2) < 3, box
                    assert abs(box["y"] + box["height"] / 2 - viewport["height"] / 2) < 3, box

                generate = page.locator("#generate-report")
                expect(generate).to_have_text("Generate", timeout=30000)
                work = page.locator("#work-requirements textarea")
                expect(work).to_have_value("")
                assert page.locator("#report-preview, iframe").count() == 0
                assert page.locator("#action-row button").count() == 3
                assert page.locator("#advanced-settings, #profiles-settings").count() == 0
                assert not page.locator("#save-config-panel").is_visible()
                assert not page.locator("#load-config-panel").is_visible()
                page.screenshot(path=str(OUTPUT / "desktop-en.png"), full_page=True)

                work.fill("Unreal 性能分析")
                page.locator("#active-language").get_by_role("combobox").click()
                page.get_by_role("option", name="简体中文", exact=True).click()
                expect(generate).to_have_text("生成报告")
                expect(work).to_have_value("Unreal 性能分析")
                page.locator("#save-config").click()
                page.locator("#profile-name textarea").fill("游戏工作")
                page.locator("#save-config-panel").get_by_role(
                    "button", name="保存", exact=True
                ).click()
                expect(page.locator("#operation-status")).to_contain_text("已保存配置")
                dismiss_feedback()
                assert load_config(workspace / "configs/游戏工作.yaml")["work_requirements"] == {
                    "description": "Unreal 性能分析",
                }
                work.fill("")
                page.locator("#load-config").click()
                page.locator("#load-config-panel").get_by_role(
                    "button", name="加载", exact=True
                ).click()
                expect(page.locator("#operation-status")).to_contain_text("已加载配置")
                dismiss_feedback()
                expect(work).to_have_value("Unreal 性能分析")
                assert not page.locator("#load-config-panel").is_visible()
                previous_report = (workspace / "output/reports/index.html").read_bytes()
                work.fill("simulate error")
                generate.click()
                expect(dialog).to_have_attribute("data-kind", "loading")
                expect(generate).to_be_disabled()
                assert_dialog_centered()
                page.keyboard.press("Escape")
                expect(dialog).to_be_visible()
                page.screenshot(path=str(OUTPUT / "loading-dialog.png"))
                expect(dialog).to_have_attribute("data-kind", "error", timeout=30000)
                assert_dialog_centered()
                expect(dialog.locator("p")).to_contain_text("Model request failed <img")
                assert dialog.locator("img").count() == 0
                assert not opened.exists()
                assert (workspace / "output/reports/index.html").read_bytes() == previous_report
                page.screenshot(path=str(OUTPUT / "error-dialog.png"))
                page.keyboard.press("Enter")
                expect(dialog).not_to_be_visible()
                expect(work).to_have_value("simulate error")
                expect(generate).to_be_enabled()
                assert page.locator("#work-requirements .error:visible").count() == 0
                work.fill("Unreal 性能分析")
                generate.click()
                expect(dialog).to_have_attribute("data-kind", "loading")
                expect(page.locator("#operation-status")).to_contain_text("1 个项目", timeout=30000)
                expect(dialog).to_have_attribute("data-kind", "success")
                page.screenshot(path=str(OUTPUT / "success-dialog.png"))
                dismiss_feedback()
                assert (
                    opened.read_text(encoding="utf-8")
                    == (workspace / "output/reports/index.html").as_uri()
                )
                report = browser.new_page()
                report.goto(opened.read_text(encoding="utf-8"))
                expect(report.locator("html")).to_have_attribute("lang", "zh-CN")
                expect(report.locator("article.project")).to_have_count(1)
                expect(report.locator(".work-match")).to_contain_text("performance-analysis")
                report.close()

                work.fill("")
                generate.click()
                expect(page.locator("#operation-status")).to_contain_text("2 个项目", timeout=30000)
                expect(dialog).to_have_attribute("data-kind", "success")
                page.set_viewport_size({"width": 390, "height": 844})
                assert_dialog_centered()
                box = dialog.bounding_box()
                assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390
                page.screenshot(path=str(OUTPUT / "success-dialog-mobile.png"))
                dismiss_feedback()
                assert load_config(workspace / "conf.yaml")["work_requirements"] == {
                    "description": "",
                }
                saved = json.loads(snapshot_path.read_text(encoding="utf-8"))
                assert all("work_match" not in repo for repo in saved["repositories"])
                saved_config = load_config(workspace / "conf.yaml")
                assert saved_config["top_n"] == 7
                assert saved_config["programming_language"] == "rust"
                assert saved_config["readme"]["workers"] == 2
                for width, height in [
                    (1920, 1080),
                    (1440, 1000),
                    (1280, 800),
                    (768, 1024),
                    (390, 844),
                    (320, 740),
                ]:
                    page.set_viewport_size({"width": width, "height": height})
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(150)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                        width
                    )
                    box = generate.bounding_box()
                    assert box and box["y"] + box["height"] <= height, (width, box)
                    page.screenshot(path=str(OUTPUT / f"ui-{width}.png"), full_page=True)
                page.reload()
                expect(generate).to_have_text("生成报告")
                expect(work).to_have_value("")
                page.locator("#load-config").click()
                page.locator("#saved-profile").get_by_role("combobox").click()
                page.get_by_role("option", name="游戏工作", exact=True).click()
                page.locator("#load-config-panel").get_by_role(
                    "button", name="加载", exact=True
                ).click()
                expect(work).to_have_value("Unreal 性能分析")
                dismiss_feedback()
                assert not errors, errors
                second = browser.new_page()
                second.goto(url)
                expect(second.locator("#generate-report")).to_have_text("生成报告")
                page.close()
                second.wait_for_timeout(9000)
                assert process.poll() is None, "Closed one tab while another remained open"
                second.reload()
                expect(second.locator("#generate-report")).to_have_text("生成报告")
                second.wait_for_timeout(9000)
                assert process.poll() is None, "Refreshing the workspace stopped the server"
                second.close()
                deadline = time.monotonic() + 20
                while process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.2)
                assert process.poll() == 0, (
                    "Server did not stop after the final workspace tab closed"
                )
                browser.close()
            print(
                "Compact UI QA passed: empty description, language switch, profiles, generation, "
                "automatic report opening, no preview, widths 320–1920, refresh/multiple tabs, "
                "automatic backend shutdown, and loading/error/success dialogs."
            )
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=20)


if __name__ == "__main__":
    main()
