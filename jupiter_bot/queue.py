from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .database import Database

STATUSES = ("PENDING", "PROCESSING", "AWAITING_HUMAN", "VERIFYING", "COMPLETED", "FAILED", "CANCELLED")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QueueManager:
    def __init__(self, db: Database):
        self.db = db

    def add(self, account_name: str, network: str) -> str:
        request_id = str(uuid.uuid4())
        timestamp = now()
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO creation_queue(id, account_name, network, status, created_at, updated_at) VALUES (?, ?, ?, 'PENDING', ?, ?)",
                (request_id, account_name.strip(), network.strip(), timestamp, timestamp),
            )
        self.db.log("QUEUE_ADDED", request_id, f"network={network.strip()}")
        return request_id

    def list(self):
        with self.db.connect() as conn:
            return conn.execute("SELECT * FROM creation_queue ORDER BY created_at").fetchall()

    def recover_interrupted(self) -> int:
        timestamp = now()
        with self.db.connect() as conn:
            cur = conn.execute(
                "UPDATE creation_queue SET status='PENDING', updated_at=?, error_message='Recovered after interrupted run' WHERE status IN ('PROCESSING','AWAITING_HUMAN','VERIFYING')",
                (timestamp,),
            )
            return cur.rowcount

    def claim_next(self):
        timestamp = now()
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM creation_queue WHERE status='PENDING' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE creation_queue SET status='PROCESSING', updated_at=? WHERE id=? AND status='PENDING'",
                (timestamp, row["id"]),
            )
            return dict(row)

    def set_status(self, request_id: str, status: str, error: str | None = None) -> None:
        if status not in STATUSES:
            raise ValueError(f"Invalid queue status: {status}")
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE creation_queue SET status=?, updated_at=?, error_message=? WHERE id=?",
                (status, now(), error, request_id),
            )
        self.db.log(f"QUEUE_{status}", request_id, error)
