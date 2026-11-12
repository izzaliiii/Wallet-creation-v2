from __future__ import annotations

import json
from pathlib import Path

from jupiter_bot.browser import BrowserManager
from jupiter_bot.config import get_settings


def main() -> None:
    settings = get_settings()
    browser = BrowserManager(settings)
    try:
        page = browser.open_onboarding()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)

        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")
        print("\nVisible page text:")
        print((page.locator("body").inner_text(timeout=10000) or "")[:12000])

        details = {
            "buttons": [],
            "links": [],
            "inputs": [],
        }
        for role in ("button", "link"):
            locator = page.get_by_role(role)
            for index in range(min(locator.count(), 100)):
                item = locator.nth(index)
                try:
                    if item.is_visible():
                        details["buttons" if role == "button" else "links"].append({
                            "name": item.inner_text(timeout=1000).strip(),
                            "aria_label": item.get_attribute("aria-label"),
                            "disabled": item.is_disabled(),
                        })
                except Exception:
                    continue

        inputs = page.locator("input")
        for index in range(min(inputs.count(), 100)):
            item = inputs.nth(index)
            try:
                if item.is_visible():
                    details["inputs"].append({
                        "type": item.get_attribute("type"),
                        "name": item.get_attribute("name"),
                        "placeholder": item.get_attribute("placeholder"),
                        "aria_label": item.get_attribute("aria-label"),
                    })
            except Exception:
                continue

        print("\nInteractive elements:")
        print(json.dumps(details, indent=2, ensure_ascii=False))

        output = settings.data_dir / "reconnaissance"
        output.mkdir(parents=True, exist_ok=True)
        screenshot = output / "onboarding-welcome.png"
        page.screenshot(path=str(screenshot), full_page=True)
        print(f"\nScreenshot saved to: {screenshot}")
        input("\nReview the page in Chrome. Press Enter to close the browser...")
    finally:
        browser.close()


if __name__ == "__main__":
    main()
