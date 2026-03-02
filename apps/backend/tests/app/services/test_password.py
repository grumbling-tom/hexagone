"""Tests for the password hashing service."""

from src.app.services.password import hash_password, verify_password


def test_hash_and_verify_round_trip():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed)


def test_different_salts_produce_different_hashes():
    hash1 = hash_password("mysecret")
    hash2 = hash_password("mysecret")
    assert hash1 != hash2


def test_wrong_password_fails():
    hashed = hash_password("mysecret")
    assert not verify_password("wrongpassword", hashed)


def test_hash_is_bcrypt_format():
    hashed = hash_password("test")
    assert hashed.startswith("$2b$")
