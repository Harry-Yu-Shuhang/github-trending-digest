"""Real UI checks in an isolated workspace; screenshots live in app/.cache/ui-browser."""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import yaml
from playwright.sync_api import expect, sync_playwright

from trending_digest.config import load_config
from trending_digest.service import run_generation

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "app/.cache/ui-browser"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="workspace ", dir=OUTPUT)).resolve()
    assert workspace.is_relative_to(OUTPUT.resolve())
    for name in ("conf.yaml", "summaries.yaml", "README.md", "docs/README.zh-CN.md"):
        (workspace / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, workspace / name)
    snapshots = sorted((ROOT / "output/data").glob("????/??/????-??-??.json"), reverse=True)
    source = snapshots[0]
    destination = workspace / source.relative_to(ROOT)
    destination.parent.mkdir(parents=True)
    shutil.copy2(source, destination)
    config = load_config(workspace / "conf.yaml")
    config["active_language"] = "en"
    snapshot = run_generation(workspace, config, cached=True)
    day = snapshot["date"]
    english_issue = workspace / f"output/reports/{day[:4]}/{day[5:7]}/{day}.html"
    english_before = english_issue.read_bytes()
    english_readme = (workspace / "README.md").read_bytes()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    errors = []
    with (OUTPUT / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "app/start.py"),
                "--root",
                str(workspace),
                "--no-browser",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, "GRADIO_ANALYTICS_ENABLED": "False", "PYTHONIOENCODING": "utf-8"},
        )
        try:
            for _ in range(240):
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
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url)
                expect(
                    page.get_by_role("button", name="Save configuration", exact=True)
                ).to_be_visible(timeout=30000)
                page.screenshot(path=str(OUTPUT / "desktop-en.png"), full_page=True)
                page.get_by_label("Programming-language filter", exact=True).fill("rust")
                page.locator("#active-language").get_by_role("combobox").click()
                page.get_by_role("option", name="简体中文", exact=True).click()
                expect(page.get_by_role("button", name="保存配置", exact=True)).to_be_visible()
                expect(page.get_by_label("编程语言筛选", exact=True)).to_have_value("rust")
                page.get_by_role("button", name="保存配置", exact=True).click()
                expect(page.locator("#operation-status")).to_contain_text("配置已保存")
                persisted = yaml.safe_load((workspace / "conf.yaml").read_text(encoding="utf-8"))
                assert persisted["active_language"] == "zh-CN"
                assert persisted["programming_language"] == "rust"
                assert "default_language" not in persisted and "languages" not in persisted
                requirements = {
                    "enabled": True,
                    "description": "查找当前工作需要的工具",
                    "keywords": [snapshot["repositories"][0]["name"]],
                    "exclude_keywords": [],
                    "min_matches": 1,
                }
                page.locator("#work-requirements textarea").fill(
                    yaml.safe_dump(requirements, allow_unicode=True, sort_keys=False)
                )
                page.get_by_label("配置名称", exact=True).fill("工作工具")
                page.get_by_role("button", name="保存命名配置", exact=True).click()
                expect(page.locator("#operation-status")).to_contain_text("已保存命名配置")
                named = workspace / "configs/工作工具.yaml"
                assert load_config(named)["work_requirements"] == requirements
                page.get_by_label("编程语言筛选", exact=True).fill("python")
                page.locator("#work-requirements textarea").fill("enabled: false")
                page.get_by_role("button", name="加载配置", exact=True).click()
                expect(page.locator("#operation-status")).to_contain_text("已加载配置")
                expect(page.get_by_label("编程语言筛选", exact=True)).to_have_value("rust")
                expect(page.locator("#work-requirements textarea")).to_have_value(
                    re.compile("查找当前工作需要的工具")
                )
                page.get_by_role("button", name="用已保存数据生成", exact=True).click()
                expect(page.locator("#operation-status")).to_contain_text(
                    "已使用保存的数据生成", timeout=30000
                )
                expect(page.locator("#report-preview iframe")).to_be_visible()
                frame = page.frame_locator("#report-preview iframe")
                expect(frame.locator("html")).to_have_attribute("lang", "zh-CN")
                expect(frame.locator("article.project")).to_have_count(1)
                expect(frame.locator(".work-match")).to_contain_text(requirements["keywords"][0])
                assert english_issue.read_bytes() == english_before
                assert (workspace / "README.md").read_bytes() == english_readme
                saved = json.loads(destination.read_text(encoding="utf-8"))
                assert all(
                    list(repo["summary"]["locales"]) == ["zh-CN"]
                    for repo in saved["repositories"][: saved["top_n"]]
                )
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
                    page.wait_for_timeout(250)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                        width
                    )
                    page.screenshot(path=str(OUTPUT / f"ui-{width}.png"))
                page.reload()
                expect(page.get_by_role("button", name="保存配置", exact=True)).to_be_visible()
                expect(page.locator("#work-requirements textarea")).to_have_value(
                    re.compile("查找当前工作需要的工具")
                )
                page.locator("#saved-profile").get_by_role("combobox").click()
                page.get_by_role("option", name="工作工具", exact=True).click()
                page.get_by_role("button", name="加载配置", exact=True).click()
                expect(page.locator("#operation-status")).to_contain_text("已加载配置")
                assert not errors, errors
                browser.close()
            print(
                "UI browser QA passed: live language switch, form preservation, saved config, "
                "named configurations, work filters, Chinese-only reports, iframe preview, "
                "persistence, widths 320–1920."
            )
        finally:
            process.terminate()
            process.wait(timeout=20)


if __name__ == "__main__":
    main()
