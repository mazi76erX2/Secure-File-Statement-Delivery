import pytest
from security import (
    InvalidPdfError,
    derive_pdf_password,
    encrypt_pdf_content,
    generate_pdf_salt,
    hash_secret,
    verify_secret,
)


def test_hash_secret_round_trip() -> None:
    secret = "9001015009087"
    stored = hash_secret(secret)

    assert verify_secret(secret, stored)
    assert not verify_secret("9001015009088", stored)


def test_verify_secret_rejects_malformed_hash() -> None:
    assert not verify_secret("anything", "invalid")
    assert not verify_secret("anything", "pbkdf2_sha256$0$bad$bad")
    assert not verify_secret("anything", "pbkdf2_sha256$abc$bad$bad")


def test_encrypt_pdf_content_rejects_invalid_pdf() -> None:
    with pytest.raises(InvalidPdfError):
        encrypt_pdf_content(b"not-a-valid-pdf", "9001015009087")


def test_pdf_password_derivation_is_deterministic() -> None:
    salt = generate_pdf_salt()

    first = derive_pdf_password("9001015009087", salt)
    second = derive_pdf_password("9001015009087", salt)

    assert first == second
    assert len(first) == 64


def test_pdf_password_derivation_rejects_invalid_salt() -> None:
    with pytest.raises(ValueError):
        derive_pdf_password("9001015009087", "bad-salt")
