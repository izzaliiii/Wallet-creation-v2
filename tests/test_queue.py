from jupiter_bot.database import Database
from jupiter_bot.queue import QueueManager


def test_queue_add_and_claim(tmp_path):
    db = Database(tmp_path / "test.sqlite3")
    db.initialize()
    queue = QueueManager(db)
    request_id = queue.add("Test Wallet", "Solana")
    claimed = queue.claim_next()
    assert claimed["id"] == request_id
    assert queue.list()[0]["status"] == "PROCESSING"


def test_interrupted_queue_recovers(tmp_path):
    db = Database(tmp_path / "test.sqlite3")
    db.initialize()
    queue = QueueManager(db)
    request_id = queue.add("Test Wallet", "Solana")
    queue.claim_next()
    assert queue.recover_interrupted() == 1
    assert queue.list()[0]["status"] == "PENDING"
