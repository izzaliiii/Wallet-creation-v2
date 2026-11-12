from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    chrome_executable: str | None
    extension_path: Path | None
    extension_id: str
    auto_lock_minutes: int

    @property
    def database_path(self) -> Path:
        return self.data_dir / "wallets.sqlite3"

    @property
    def browser_profile(self) -> Path:
        return self.data_dir / "browser-profile"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"


def get_settings() -> Settings:
    raw_data = os.getenv("JWB_DATA_DIR", "").strip()
    data_dir = Path(raw_data).expanduser() if raw_data else PROJECT_ROOT / ".jupiter-wallet-bot"
    raw_extension = os.getenv("EXTENSION_PATH", "").strip()
    extension_path = Path(raw_extension).expanduser().resolve() if raw_extension else None
    raw_timeout = os.getenv("VAULT_AUTO_LOCK_MINUTES", "10")
    try:
        auto_lock = max(1, int(raw_timeout))
    except ValueError:
        auto_lock = 10
    return Settings(
        data_dir=data_dir.resolve(),
        chrome_executable=os.getenv("CHROME_EXECUTABLE", "").strip() or None,
        extension_path=extension_path,
        extension_id=os.getenv("JUPITER_EXTENSION_ID", "iledlaeogohbilgbfhmbgkgmpplbfboh").strip(),
        auto_lock_minutes=auto_lock,
    )
