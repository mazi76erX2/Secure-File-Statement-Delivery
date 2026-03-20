import pytest
from security import InvalidPdfError, encrypt_pdf_content, hash_secret, verify_secret


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
