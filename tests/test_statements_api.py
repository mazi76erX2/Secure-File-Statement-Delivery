from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from typing import cast

import pytest
from api import statements as statements_module
from fastapi import HTTPException, UploadFile
from models import AccountStatement, Customer, StatementDownloadLink
from security import hash_secret
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers
from starlette.requests import Request


def _request(
    client_host: str = "127.0.0.1",
    forwarded_for: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for:
        headers.append((b"x-forwarded-for", forwarded_for.encode("utf-8")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


class _FakeSession:
    def __init__(
        self,
        *,
        file_path: str = "statements/1/statement.pdf",
        checksum_sha256: str | None = "a" * 64,
    ) -> None:
        self._file_path = file_path
        self._checksum_sha256 = checksum_sha256

    async def scalar(self, *_args, **_kwargs) -> StatementDownloadLink:
        return StatementDownloadLink(
            id=1,
            statement_id=1,
            token_hash="token-hash",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            max_downloads=2,
            download_count=0,
        )

    async def get(self, model, _id):
        if model is AccountStatement:
            return AccountStatement(
                id=1,
                customer_id=1,
                account_number_last4="1234",
                statement_period_start=date(2026, 2, 1),
                statement_period_end=date(2026, 2, 28),
                file_name="statement.pdf",
                file_path=self._file_path,
                content_type="application/pdf",
                file_size_bytes=123,
                checksum_sha256=self._checksum_sha256,
            )
        if model is Customer:
            return Customer(
                id=1,
                full_name="Test User",
                email="test@example.com",
                id_number_hash=hash_secret("9001015009087"),
            )
        return None

    async def commit(self) -> None:
        return None


def _pdf_upload_file(content: bytes, filename: str = "statement.pdf") -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


@pytest.mark.anyio
async def test_upload_statement_rejects_non_pdf_magic_header() -> None:
    fake_session = cast(AsyncSession, _FakeSession())

    with pytest.raises(HTTPException) as exc:
        await statements_module.upload_statement(
            customer_id=1,
            account_number_last4="1234",
            statement_period_start=date(2026, 2, 1),
            statement_period_end=date(2026, 2, 28),
            file=_pdf_upload_file(b"not-a-pdf", "bad.pdf"),
            _auth=None,
            session=fake_session,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Uploaded file is not a valid PDF document"


@pytest.mark.anyio
async def test_upload_statement_rejects_non_digit_account_number() -> None:
    fake_session = cast(AsyncSession, _FakeSession())

    with pytest.raises(HTTPException) as exc:
        await statements_module.upload_statement(
            customer_id=1,
            account_number_last4="12AB",
            statement_period_start=date(2026, 2, 1),
            statement_period_end=date(2026, 2, 28),
            file=_pdf_upload_file(b"%PDF-1.4\n", "statement.pdf"),
            _auth=None,
            session=fake_session,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "account_number_last4 must contain exactly 4 digits"


def test_extract_client_ip_uses_direct_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(statements_module.settings, "trust_proxy_headers", False)

    client_ip = statements_module._extract_client_ip(_request(client_host="10.1.2.3"))

    assert client_ip == "10.1.2.3"


def test_extract_client_ip_uses_forwarded_header_when_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(statements_module.settings, "trust_proxy_headers", True)

    client_ip = statements_module._extract_client_ip(
        _request(client_host="10.1.2.3", forwarded_for="203.0.113.25, 10.1.2.3")
    )

    assert client_ip == "203.0.113.25"


@pytest.mark.anyio
async def test_enforce_download_rate_limit_blocks_when_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        statements_module.settings, "statement_download_rate_limit_requests", 2
    )
    monkeypatch.setattr(
        statements_module.settings, "statement_download_rate_limit_window_seconds", 60
    )

    async def _fake_incr(_key: str, _expire_seconds: int) -> int:
        return 3

    monkeypatch.setattr(statements_module.redis_cache, "incr_with_expiry", _fake_incr)

    with pytest.raises(HTTPException) as exc:
        await statements_module._enforce_download_rate_limit(_request())

    assert exc.value.status_code == 429
    assert exc.value.headers == {"Retry-After": "60"}


@pytest.mark.anyio
async def test_download_rejects_bad_id_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = cast(AsyncSession, _FakeSession())

    async def _fake_rate_limit(_request: Request) -> None:
        return None

    monkeypatch.setattr(
        statements_module, "_enforce_download_rate_limit", _fake_rate_limit
    )

    with pytest.raises(HTTPException) as exc:
        await statements_module.download_statement(
            token="test-token",
            request=_request(),
            x_id_number="123",
            session=fake_session,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid or missing customer ID number"


@pytest.mark.anyio
async def test_download_returns_404_when_storage_file_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = cast(AsyncSession, _FakeSession(file_path="../outside.pdf"))

    async def _fake_rate_limit(_request: Request) -> None:
        return None

    def _fake_read_pdf(_path: str) -> bytes:
        raise FileNotFoundError("Statement file is unavailable")

    monkeypatch.setattr(
        statements_module, "_enforce_download_rate_limit", _fake_rate_limit
    )
    monkeypatch.setattr(statements_module.storage_service, "read_pdf", _fake_read_pdf)
    monkeypatch.setattr(statements_module, "verify_secret", lambda *_args: True)

    with pytest.raises(HTTPException) as exc:
        await statements_module.download_statement(
            token="test-token",
            request=_request(),
            x_id_number="9001015009087",
            session=fake_session,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Statement file is unavailable"
