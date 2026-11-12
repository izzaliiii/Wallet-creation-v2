import pytest

from jupiter_bot.security import decrypt_secret, derive_key, encrypt_secret, new_salt


def test_encrypt_decrypt_roundtrip():
    key = derive_key("a-strong-test-password-123", new_salt())
    encrypted = encrypt_secret(key, "test secret", b"wallet:recovery_phrase")
    assert decrypt_secret(key, encrypted.ciphertext, encrypted.nonce, b"wallet:recovery_phrase") == "test secret"


def test_wrong_associated_data_fails():
    key = derive_key("a-strong-test-password-123", new_salt())
    encrypted = encrypt_secret(key, "test secret", b"wallet:recovery_phrase")
    with pytest.raises(Exception):
        decrypt_secret(key, encrypted.ciphertext, encrypted.nonce, b"wallet:private_key")


def test_password_minimum_length():
    with pytest.raises(ValueError):
        derive_key("short", new_salt())
