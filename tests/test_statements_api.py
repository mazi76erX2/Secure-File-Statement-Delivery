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
        "router": statements_module.router,
    }
    return Request(scope)


class _FakeSession:
    def __init__(
        self,
        *,
        file_path: str = "statements/1/statement.pdf",
        checksum_sha256: str | None = "a" * 64,
        customer_pdf_salt: str | None = "a" * 64,
    ) -> None:
        self._file_path = file_path
        self._checksum_sha256 = checksum_sha256
        self._customer_pdf_salt = customer_pdf_salt

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
                pdf_salt=self._customer_pdf_salt,
            )
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, _instance) -> None:
        return None


def _pdf_upload_file(content: bytes, filename: str = "statement.pdf") -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


def _fake_download_link(*, revoked_at: datetime | None = None) -> StatementDownloadLink:
    return StatementDownloadLink(
        id=1,
        statement_id=1,
        token_hash="token-hash",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        max_downloads=2,
        download_count=0,
        revoked_at=revoked_at,
    )


class _RevokeSession(_FakeSession):
    def __init__(self, link: StatementDownloadLink | None) -> None:
        super().__init__()
        self._link = link

    async def get(self, model, _id):
        if model is StatementDownloadLink:
            return self._link
        return await super().get(model, _id)


class _BulkLinksSession(_FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self._next_link_id = 100

    async def get(self, model, _id):
        if model is Customer:
            return Customer(
                id=1,
                full_name="Bulk User",
                email="bulk@example.com",
                id_number_hash=hash_secret("9001015009087"),
                pdf_salt="a" * 64,
            )
        return await super().get(model, _id)

    async def scalars(self, *_args, **_kwargs):
        statement = AccountStatement(
            id=2,
            customer_id=1,
            account_number_last4="5678",
            statement_period_start=date(2026, 2, 1),
            statement_period_end=date(2026, 2, 28),
            file_name="bulk.pdf",
            file_path="statements/1/bulk.pdf",
            content_type="application/pdf",
            file_size_bytes=123,
            checksum_sha256=None,
        )
        return [statement]

    def add(self, _obj) -> None:
        if isinstance(_obj, StatementDownloadLink):
            now = datetime.now(UTC)
            _obj.id = self._next_link_id
            self._next_link_id += 1
            _obj.download_count = 0
            _obj.created_at = now
            _obj.updated_at = now
        return None

    async def flush(self) -> None:
        return None


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


@pytest.mark.anyio
async def test_download_uses_derived_pdf_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = cast(AsyncSession, _FakeSession(checksum_sha256=None))

    async def _fake_rate_limit(_request: Request) -> None:
        return None

    def _fake_read_pdf(_path: str) -> bytes:
        return b"%PDF-1.4\nmock"

    def _fake_derive_pdf_password(
        _id_number: str,
        _pdf_salt_hex: str,
        _iterations: int = 600_000,
    ) -> str:
        return "derived-password"

    def _fake_encrypt_pdf_content(_pdf_content: bytes, password: str) -> bytes:
        assert password == "derived-password"
        return b"%PDF-1.7\nencrypted"

    monkeypatch.setattr(
        statements_module, "_enforce_download_rate_limit", _fake_rate_limit
    )
    monkeypatch.setattr(statements_module.storage_service, "read_pdf", _fake_read_pdf)
    monkeypatch.setattr(statements_module, "verify_secret", lambda *_args: True)
    monkeypatch.setattr(
        statements_module,
        "derive_pdf_password",
        _fake_derive_pdf_password,
    )
    monkeypatch.setattr(
        statements_module,
        "encrypt_pdf_content",
        _fake_encrypt_pdf_content,
    )

    response = await statements_module.download_statement(
        token="test-token",
        request=_request(),
        x_id_number="9001015009087",
        session=fake_session,
    )

    assert response.status_code == 200
    assert response.body.startswith(b"%PDF-1.7")


@pytest.mark.anyio
async def test_download_generates_missing_pdf_salt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = cast(
        AsyncSession,
        _FakeSession(checksum_sha256=None, customer_pdf_salt=None),
    )

    async def _fake_rate_limit(_request: Request) -> None:
        return None

    def _fake_read_pdf(_path: str) -> bytes:
        return b"%PDF-1.4\nmock"

    def _fake_generate_pdf_salt() -> str:
        return "b" * 64

    monkeypatch.setattr(
        statements_module, "_enforce_download_rate_limit", _fake_rate_limit
    )
    monkeypatch.setattr(statements_module.storage_service, "read_pdf", _fake_read_pdf)
    monkeypatch.setattr(statements_module, "verify_secret", lambda *_args: True)
    monkeypatch.setattr(
        statements_module,
        "generate_pdf_salt",
        _fake_generate_pdf_salt,
    )

    def _fake_derive_pdf_password(
        _id_number: str,
        pdf_salt_hex: str,
        _iterations: int = 600_000,
    ) -> str:
        assert pdf_salt_hex == "b" * 64
        return "derived-password"

    monkeypatch.setattr(
        statements_module, "derive_pdf_password", _fake_derive_pdf_password
    )
    monkeypatch.setattr(
        statements_module,
        "encrypt_pdf_content",
        lambda *_args: b"%PDF-1.7\nencrypted",
    )

    response = await statements_module.download_statement(
        token="test-token",
        request=_request(),
        x_id_number="9001015009087",
        session=fake_session,
    )

    assert response.status_code == 200


@pytest.mark.anyio
async def test_revoke_download_link_sets_timestamp() -> None:
    link = _fake_download_link()
    fake_session = cast(AsyncSession, _RevokeSession(link))

    response = await statements_module.revoke_download_link(
        link_id=1,
        _auth=None,
        session=fake_session,
    )

    assert response.id == 1
    assert response.revoked_at is not None


@pytest.mark.anyio
async def test_revoke_download_link_not_found() -> None:
    fake_session = cast(AsyncSession, _RevokeSession(None))

    with pytest.raises(HTTPException) as exc:
        await statements_module.revoke_download_link(
            link_id=99,
            _auth=None,
            session=fake_session,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Download link not found"


@pytest.mark.anyio
async def test_issue_month_range_links_endpoint_still_works() -> None:
    fake_session = cast(AsyncSession, _BulkLinksSession())

    response = await statements_module.issue_month_range_links(
        customer_id=1,
        payload=statements_module.StatementDownloadLinkCreate(
            expires_in_seconds=3600,
            max_downloads=2,
        ),
        request=_request(),
        from_month="2026-02",
        to_month="2026-02",
        _auth=None,
        session=fake_session,
    )

    assert len(response) == 1
    assert response[0].statement_id == 2


def test_month_range_links_route_has_distinct_path() -> None:
    paths = {
        route.path
        for route in statements_module.router.routes
        if "POST" in getattr(route, "methods", set())
    }
    assert any(path.endswith("/{statement_id}/links") for path in paths)
    assert any(path.endswith("/{customer_id}/links/bulk") for path in paths)
