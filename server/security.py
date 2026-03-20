"""Security utilities for hashing and PDF password protection."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from io import BytesIO


class InvalidPdfError(ValueError):
    """Raised when stored PDF content cannot be encrypted safely."""


def generate_pdf_salt() -> str:
    return secrets.token_hex(32)


def derive_pdf_password(
    id_number: str, pdf_salt_hex: str, iterations: int = 600_000
) -> str:
    if iterations <= 0:
        raise ValueError("PDF key derivation iterations must be positive")

    try:
        pdf_salt = bytes.fromhex(pdf_salt_hex)
    except ValueError as exc:
        raise ValueError("PDF key derivation salt must be hex-encoded") from exc

    if len(pdf_salt) != 32:
        raise ValueError("PDF key derivation salt must be exactly 32 bytes")

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        id_number.encode("utf-8"),
        pdf_salt,
        iterations,
    )
    return derived.hex()


def hash_secret(secret: str, iterations: int = 300_000) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("utf-8"),
        base64.urlsafe_b64encode(derived).decode("utf-8"),
    )


def verify_secret(secret: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        if iterations <= 0:
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
        expected_digest = base64.urlsafe_b64decode(digest_b64.encode("utf-8"))
    except ValueError:
        return False
    except TypeError:
        return False
    except binascii.Error:
        return False

    calculated = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(calculated, expected_digest)


def encrypt_pdf_content(pdf_content: bytes, password: str) -> bytes:
    import pikepdf

    output = BytesIO()
    try:
        with pikepdf.open(BytesIO(pdf_content)) as pdf:
            pdf.save(
                output,
                encryption=pikepdf.Encryption(
                    owner=password,
                    user=password,
                    R=6,
                ),
            )
    except pikepdf.PdfError as exc:
        raise InvalidPdfError("Invalid PDF content") from exc

    return output.getvalue()
