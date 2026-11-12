from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS wallets (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    public_address TEXT NOT NULL UNIQUE,
    network TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
);
CREATE TABLE IF NOT EXISTS creation_queue (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    network TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS encrypted_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id TEXT NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
    secret_type TEXT NOT NULL,
    ciphertext BLOB NOT NULL,
    nonce BLOB NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(wallet_id, secret_type)
);
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,
    entity_id TEXT,
    details TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_queue_status_created ON creation_queue(status, created_at);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def log(self, event: str, entity_id: str | None = None, details: str | None = None) -> None:
        from datetime import datetime, timezone
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO activity_logs(event, entity_id, details, created_at) VALUES (?, ?, ?, ?)",
                (event, entity_id, details, datetime.now(timezone.utc).isoformat()),
            )
