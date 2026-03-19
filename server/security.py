"""Security utilities for hashing and PDF password protection."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from io import BytesIO

import pikepdf


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
        salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
        expected_digest = base64.urlsafe_b64decode(digest_b64.encode("utf-8"))
    except (ValueError, TypeError):
        return False

    calculated = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(calculated, expected_digest)


def encrypt_pdf_content(pdf_content: bytes, password: str) -> bytes:
    output = BytesIO()

    with pikepdf.open(BytesIO(pdf_content)) as pdf:
        pdf.save(
            output,
            encryption=pikepdf.Encryption(
                owner=password,
                user=password,
                R=6,
            ),
        )

    return output.getvalue()
