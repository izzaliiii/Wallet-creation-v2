from __future__ import annotations

import os
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KDF_TIME_COST = 3
KDF_MEMORY_COST_KIB = 65536
KDF_PARALLELISM = 2
KEY_LENGTH = 32
SALT_LENGTH = 16
NONCE_LENGTH = 12


@dataclass(frozen=True)
class EncryptedValue:
    ciphertext: bytes
    nonce: bytes


def derive_key(password: str, salt: bytes) -> bytes:
    if len(password) < 12:
        raise ValueError("Master password must contain at least 12 characters.")
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=KDF_TIME_COST,
        memory_cost=KDF_MEMORY_COST_KIB,
        parallelism=KDF_PARALLELISM,
        hash_len=KEY_LENGTH,
        type=Type.ID,
    )


def new_salt() -> bytes:
    return os.urandom(SALT_LENGTH)


def encrypt_secret(key: bytes, plaintext: str, associated_data: bytes) -> EncryptedValue:
    nonce = os.urandom(NONCE_LENGTH)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), associated_data)
    return EncryptedValue(ciphertext=ciphertext, nonce=nonce)


def decrypt_secret(key: bytes, ciphertext: bytes, nonce: bytes, associated_data: bytes) -> str:
    return AESGCM(key).decrypt(nonce, ciphertext, associated_data).decode("utf-8")
