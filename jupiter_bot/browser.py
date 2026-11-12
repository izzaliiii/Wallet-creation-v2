from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from .config import Settings


class BrowserManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._playwright = None
        self.context = None

    def launch(self):
        extension = self.settings.extension_path
        if not extension or not extension.is_dir():
            raise FileNotFoundError("Set EXTENSION_PATH in .env to a verified unpacked extension directory.")
        manifest = extension / "manifest.json"
        if not manifest.is_file():
            raise FileNotFoundError(f"manifest.json not found in extension directory: {extension}")
        self.settings.browser_profile.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        args = [
            f"--disable-extensions-except={extension}",
            f"--load-extension={extension}",
        ]
        launch_options = {
            "user_data_dir": str(self.settings.browser_profile),
            "headless": False,
            "args": args,
        }
        if self.settings.chrome_executable:
            launch_options["executable_path"] = self.settings.chrome_executable
        self.context = self._playwright.chromium.launch_persistent_context(**launch_options)
        return self.context

    def open_onboarding(self):
        if not self.context:
            self.launch()
        page = self.context.new_page()
        extension_url = f"chrome-extension://{self.settings.extension_id}/popup.html#/onboard"
        page.goto(extension_url, wait_until="domcontentloaded", timeout=30000)
        return page

    def close(self):
        if self.context:
            self.context.close()
            self.context = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
