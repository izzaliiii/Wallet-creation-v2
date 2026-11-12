from __future__ import annotations

import getpass
import re
import uuid
from datetime import datetime, timezone

from .browser import BrowserManager
from .database import Database
from .queue import QueueManager
from .vault import Vault

ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class WalletWorkflow:
    def __init__(self, db: Database, queue: QueueManager, vault: Vault, browser: BrowserManager):
        self.db, self.queue, self.vault, self.browser = db, queue, vault, browser

    def process_queue(self) -> None:
        recovered = self.queue.recover_interrupted()
        if recovered:
            print(f"Recovered {recovered} interrupted request(s).")
        while True:
            item = self.queue.claim_next()
            if item is None:
                print("Queue is empty.")
                return
            request_id = item["id"]
            print(f"\nProcessing: {item['account_name']} ({request_id[:8]})")
            try:
                self.queue.set_status(request_id, "AWAITING_HUMAN")
                page = self.browser.open_onboarding()
                print(f"Opened extension onboarding: {page.url}")
                print("\nComplete the wallet provider's onboarding yourself.")
                print("Do not paste a recovery phrase into chat, logs, or screenshots.")
                input("When the wallet is created and visible in the extension, press Enter here...")
                address = input("Enter the wallet's PUBLIC address shown by the extension: ").strip()
                if not ADDRESS_RE.fullmatch(address):
                    raise ValueError("Address does not match the expected base58 public-address format.")
                with self.db.connect() as conn:
                    duplicate = conn.execute("SELECT id FROM wallets WHERE public_address=?", (address,)).fetchone()
                if duplicate:
                    raise ValueError("This public address is already saved; refusing duplicate wallet record.")
                self.queue.set_status(request_id, "VERIFYING")
                confirm = input(f"Confirm this public address belongs to {item['account_name']} on {item['network']}? Type SAVE to continue: ").strip()
                if confirm != "SAVE":
                    self.queue.set_status(request_id, "CANCELLED", "User declined metadata save.")
                    continue
                wallet_id = str(uuid.uuid4())
                created_at = datetime.now(timezone.utc).isoformat()
                with self.db.connect() as conn:
                    conn.execute(
                        "INSERT INTO wallets(id, account_name, public_address, network, created_at, status) VALUES (?, ?, ?, ?, ?, 'ACTIVE')",
                        (wallet_id, item["account_name"], address, item["network"], created_at),
                    )
                self.queue.set_status(request_id, "COMPLETED")
                self.db.log("WALLET_SAVED", wallet_id, f"queue_id={request_id}; network={item['network']}")
                print(f"Saved wallet metadata. ID: {wallet_id}")
                choice = input("Store an explicitly exported recovery phrase/private key in the encrypted vault? [y/N]: ").strip().lower()
                if choice == "y":
                    print("Only proceed if you personally exported the secret through the wallet's official UI.")
                    secret_type = input("Secret type (recovery_phrase/private_key): ").strip()
                    if secret_type not in {"recovery_phrase", "private_key"}:
                        print("Unsupported secret type; skipping.")
                    else:
                        secret = getpass.getpass("Secret (hidden input; never echoed): ")
                        if secret:
                            encrypted = self.vault.encrypt(secret, wallet_id, secret_type)
                            with self.db.connect() as conn:
                                conn.execute(
                                    "INSERT INTO encrypted_credentials(wallet_id, secret_type, ciphertext, nonce, created_at) VALUES (?, ?, ?, ?, ?)",
                                    (wallet_id, secret_type, encrypted.ciphertext, encrypted.nonce, created_at),
                                )
                            self.db.log("SECRET_ENCRYPTED", wallet_id, secret_type)
                        secret = ""
            except KeyboardInterrupt:
                self.queue.set_status(request_id, "PENDING", "Interrupted by user; safe to resume.")
                print("\nStopped by user.")
                return
            except Exception as exc:
                self.queue.set_status(request_id, "FAILED", str(exc)[:300])
                print(f"Request failed: {exc}")
