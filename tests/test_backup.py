from pathlib import Path

import pytest

from jupiter_bot.vault import Vault


def test_encrypted_backup_roundtrip(tmp_path: Path):
    vault = Vault(tmp_path)
    vault._key = b"t" * 32  # Inject a test-only key; production keys come from Argon2id.
    database = b"SQLite test fixture bytes"
    encrypted = vault.encrypt_backup(database)
    assert encrypted.startswith(b"JWB1")
    assert vault.decrypt_backup(encrypted) == database


def test_backup_tampering_is_rejected(tmp_path: Path):
    vault = Vault(tmp_path)
    vault._key = b"t" * 32
    encrypted = bytearray(vault.encrypt_backup(b"database"))
    encrypted[-1] ^= 0x01
    with pytest.raises(Exception):
        vault.decrypt_backup(bytes(encrypted))
