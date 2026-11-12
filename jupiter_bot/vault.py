from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .security import decrypt_secret, derive_key, encrypt_secret, new_salt


class Vault:
    """In-memory unlocked vault. The derived key is never persisted."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.header_path = data_dir / "vault.json"
        self._key: bytes | None = None

    @property
    def is_unlocked(self) -> bool:
        return self._key is not None

    def initialize_or_unlock(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.header_path.exists():
            print("Create a strong vault master password (12+ characters).")
            first = getpass.getpass("New master password: ")
            second = getpass.getpass("Confirm master password: ")
            if first != second:
                raise ValueError("Passwords do not match.")
            salt = new_salt()
            key = derive_key(first, salt)
            verifier = encrypt_secret(key, "jupiter-wallet-bot-vault-check", b"vault-verifier")
            payload = {
                "version": 1,
                "kdf": "argon2id",
                "salt": salt.hex(),
                "verifier_nonce": verifier.nonce.hex(),
                "verifier_ciphertext": verifier.ciphertext.hex(),
            }
            temporary = self.header_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            temporary.replace(self.header_path)
            self._key = key
            return

        payload = json.loads(self.header_path.read_text(encoding="utf-8"))
        if payload.get("version") != 1 or payload.get("kdf") != "argon2id":
            raise ValueError("Unsupported vault header version.")
        password = getpass.getpass("Vault master password: ")
        key = derive_key(password, bytes.fromhex(payload["salt"]))
        try:
            check = decrypt_secret(
                key,
                bytes.fromhex(payload["verifier_ciphertext"]),
                bytes.fromhex(payload["verifier_nonce"]),
                b"vault-verifier",
            )
        except Exception as exc:
            raise ValueError("Incorrect master password or damaged vault header.") from exc
        if check != "jupiter-wallet-bot-vault-check":
            raise ValueError("Vault verification failed.")
        self._key = key

    def lock(self) -> None:
        self._key = None

    def encrypt(self, secret: str, wallet_id: str, secret_type: str):
        if not self._key:
            raise RuntimeError("Vault is locked.")
        aad = f"{wallet_id}:{secret_type}".encode()
        return encrypt_secret(self._key, secret, aad)

    def decrypt(self, ciphertext: bytes, nonce: bytes, wallet_id: str, secret_type: str) -> str:
        if not self._key:
            raise RuntimeError("Vault is locked.")
        aad = f"{wallet_id}:{secret_type}".encode()
        return decrypt_secret(self._key, ciphertext, nonce, aad)

    def encrypt_backup(self, database_bytes: bytes) -> bytes:
        """Encrypt an entire SQLite backup; format = magic + nonce + AES-GCM ciphertext."""
        if not self._key:
            raise RuntimeError("Vault is locked.")
        nonce = os.urandom(12)
        return b"JWB1" + nonce + AESGCM(self._key).encrypt(
            nonce, database_bytes, b"jupiter-wallet-bot-database-backup-v1"
        )
