"""Optional browser QA: uv run --with playwright python tests/browser_smoke.py."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / ".cache/browser"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
        / "Google/Chrome/Application/chrome.exe",
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    ]
    executable = next((str(path) for path in candidates if path.exists()), None)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, color_scheme="light")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "reports/index.html").as_uri())
        total = page.locator(".project").count()
        assert total > 0
        assert page.locator(".project:visible").count() == total
        page.locator("#search").fill("unlikely-query-no-match-12345")
        assert page.locator(".project:visible").count() == 0
        assert page.locator("#empty-state").is_visible()
        page.locator("#reset").click()
        assert page.locator(".project:visible").count() == total
        language = page.locator(".project").first.get_attribute("data-language")
        page.select_option("#technology", language)
        expected = page.locator(".project").evaluate_all(
            "(cards, language) => cards.filter(card => card.dataset.language === language).length",
            language,
        )
        assert page.locator(".project:visible").count() == expected
        page.locator("#reset").click()
        page.screenshot(path=str(OUTPUT / "desktop.png"))
        page.locator("#theme").click()
        assert page.locator("html").get_attribute("data-theme") == "dark"
        page.screenshot(path=str(OUTPUT / "dark.png"))
        page.locator("#theme").click()
        assert page.locator(".locale-switch a").count() == 1
        assert page.locator(".locale-switch a").get_attribute("lang") == page.locator(
            "html"
        ).get_attribute("lang")
        assert page.locator(".project:visible").count() == total
        page.screenshot(path=str(OUTPUT / "chinese.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(OUTPUT / "mobile.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#jump").is_visible()
        target = page.locator(".project").nth(min(1, total - 1)).get_attribute("id")
        page.select_option("#jump", target)
        page.wait_for_timeout(500)
        assert page.evaluate("window.scrollY > 0")
        page.emulate_media(media="print")
        assert not page.locator(".reading-tools").is_visible()
        page.pdf(path=str(OUTPUT / "print-preview.pdf"), format="A4", print_background=True)
        page.emulate_media(media="screen")
        page.goto((ROOT / "reports/archive.html").as_uri())
        page.locator(".archive-issue").first.click()
        assert page.locator(".project:visible").count() == total
        assert not errors, errors
        browser.close()
        print(
            f"Browser QA passed: {total} projects; search, filters, theme, "
            "locales, mobile, archive, print."
        )


if __name__ == "__main__":
    main()
