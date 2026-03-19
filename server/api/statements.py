"""Statement delivery API routes."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, date, datetime, timedelta

from config import settings
from database import get_session
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from models import AccountStatement, Customer, StatementDownloadLink
from schemas import (
    AccountStatementResponse,
    CustomerCreate,
    CustomerResponse,
    StatementDownloadLinkCreate,
    StatementDownloadLinkIssued,
)
from security import encrypt_pdf_content, hash_secret, verify_secret
from services.document_storage import DocumentStorageService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/statements", tags=["statements"])
storage_service = DocumentStorageService(settings)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_month(month_value: str) -> date:
    try:
        parsed = datetime.strptime(month_value, "%Y-%m").date()
        return parsed.replace(day=1)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Month values must be in YYYY-MM format",
        ) from exc


def _resolve_month_range(
    from_month: str | None, to_month: str | None
) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    first_day_this_month = today.replace(day=1)

    if from_month is None and to_month is None:
        last_day_previous_month = first_day_this_month - timedelta(days=1)
        start = last_day_previous_month.replace(day=1)
        end = last_day_previous_month
        return start, end

    if from_month is None:
        raise HTTPException(
            status_code=400, detail="from_month is required when to_month is provided"
        )

    start_month = _parse_month(from_month)
    end_month = _parse_month(to_month) if to_month else start_month

    if end_month < start_month:
        raise HTTPException(
            status_code=400,
            detail="to_month must be greater than or equal to from_month",
        )

    if end_month.year == today.year and end_month.month == today.month:
        end = today
    else:
        if end_month.month == 12:
            first_day_next_month = date(end_month.year + 1, 1, 1)
        else:
            first_day_next_month = date(end_month.year, end_month.month + 1, 1)
        end = first_day_next_month - timedelta(days=1)

    return start_month, end


async def require_admin_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    configured_api_key = getattr(settings, "statement_api_key", None)

    if not configured_api_key:
        raise HTTPException(
            status_code=503,
            detail="Statement API key is not configured on the server",
        )

    if x_api_key is None or not hmac.compare_digest(x_api_key, configured_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    payload: CustomerCreate,
    _auth: None = Depends(require_admin_api_key),
    session: AsyncSession = Depends(get_session),
) -> CustomerResponse:
    existing_customer = await session.scalar(
        select(Customer).where(Customer.email == payload.email)
    )
    if existing_customer:
        raise HTTPException(status_code=409, detail="Customer email already exists")

    customer = Customer(
        full_name=payload.full_name,
        email=payload.email,
        id_number_hash=hash_secret(payload.id_number),
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return CustomerResponse(
        id=customer.id,
        full_name=customer.full_name,
        email=customer.email,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        id_number_configured=customer.id_number_hash is not None,
    )


@router.post(
    "/{customer_id}/upload",
    response_model=AccountStatementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_statement(
    customer_id: int,
    account_number_last4: str = Form(..., min_length=4, max_length=4),
    statement_period_start: date = Form(...),
    statement_period_end: date = Form(...),
    file: UploadFile = File(...),
    _auth: None = Depends(require_admin_api_key),
    session: AsyncSession = Depends(get_session),
) -> AccountStatement:
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if statement_period_end < statement_period_start:
        raise HTTPException(
            status_code=400,
            detail="statement_period_end must be on or after statement_period_start",
        )

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    generated_name = file.filename or "statement.pdf"
    stored_object_key = storage_service.save_pdf(content, customer_id, generated_name)

    statement = AccountStatement(
        customer_id=customer_id,
        account_number_last4=account_number_last4,
        statement_period_start=statement_period_start,
        statement_period_end=statement_period_end,
        file_name=file.filename or generated_name,
        file_path=stored_object_key,
        content_type=file.content_type,
        file_size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
    )
    session.add(statement)
    await session.commit()
    await session.refresh(statement)
    return statement


@router.post(
    "/{statement_id}/links",
    response_model=StatementDownloadLinkIssued,
    status_code=status.HTTP_201_CREATED,
)
async def issue_download_link(
    statement_id: int,
    payload: StatementDownloadLinkCreate,
    request: Request,
    _auth: None = Depends(require_admin_api_key),
    session: AsyncSession = Depends(get_session),
) -> StatementDownloadLinkIssued:
    statement = await session.get(AccountStatement, statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = datetime.now(UTC) + timedelta(seconds=payload.expires_in_seconds)

    link = StatementDownloadLink(
        statement_id=statement_id,
        token_hash=token_hash,
        expires_at=expires_at,
        max_downloads=payload.max_downloads,
    )

    session.add(link)
    await session.commit()
    await session.refresh(link)

    download_url = str(request.url_for("download_statement", token=token))

    return StatementDownloadLinkIssued(
        id=link.id,
        statement_id=link.statement_id,
        expires_at=link.expires_at,
        max_downloads=link.max_downloads,
        download_count=link.download_count,
        last_downloaded_at=link.last_downloaded_at,
        revoked_at=link.revoked_at,
        created_at=link.created_at,
        updated_at=link.updated_at,
        token=token,
        download_url=download_url,
    )


@router.get("/{customer_id}", response_model=list[AccountStatementResponse])
async def list_customer_statements(
    customer_id: int,
    from_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    to_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    _auth: None = Depends(require_admin_api_key),
    session: AsyncSession = Depends(get_session),
) -> list[AccountStatement]:
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    start_date, end_date = _resolve_month_range(from_month, to_month)

    statements = await session.scalars(
        select(AccountStatement)
        .where(AccountStatement.customer_id == customer_id)
        .where(AccountStatement.statement_period_start >= start_date)
        .where(AccountStatement.statement_period_end <= end_date)
        .order_by(AccountStatement.statement_period_start.desc())
    )
    return list(statements)


@router.post(
    "/{customer_id}/links",
    response_model=list[StatementDownloadLinkIssued],
    status_code=status.HTTP_201_CREATED,
)
async def issue_month_range_links(
    customer_id: int,
    payload: StatementDownloadLinkCreate,
    request: Request,
    from_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    to_month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    _auth: None = Depends(require_admin_api_key),
    session: AsyncSession = Depends(get_session),
) -> list[StatementDownloadLinkIssued]:
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    start_date, end_date = _resolve_month_range(from_month, to_month)
    statements = await session.scalars(
        select(AccountStatement)
        .where(AccountStatement.customer_id == customer_id)
        .where(AccountStatement.statement_period_start >= start_date)
        .where(AccountStatement.statement_period_end <= end_date)
        .order_by(AccountStatement.statement_period_start.desc())
    )
    statement_list = list(statements)
    if not statement_list:
        return []

    issued_links: list[tuple[StatementDownloadLink, str]] = []
    for statement in statement_list:
        token = secrets.token_urlsafe(32)
        link = StatementDownloadLink(
            statement_id=statement.id,
            token_hash=_hash_token(token),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=payload.expires_in_seconds),
            max_downloads=payload.max_downloads,
        )
        session.add(link)
        await session.flush()
        issued_links.append((link, token))

    await session.commit()

    response_payload: list[StatementDownloadLinkIssued] = []
    for link, token in issued_links:
        await session.refresh(link)
        response_payload.append(
            StatementDownloadLinkIssued(
                id=link.id,
                statement_id=link.statement_id,
                expires_at=link.expires_at,
                max_downloads=link.max_downloads,
                download_count=link.download_count,
                last_downloaded_at=link.last_downloaded_at,
                revoked_at=link.revoked_at,
                created_at=link.created_at,
                updated_at=link.updated_at,
                token=token,
                download_url=str(request.url_for("download_statement", token=token)),
            )
        )

    return response_payload


@router.get("/download/{token}", name="download_statement")
async def download_statement(
    token: str,
    x_id_number: str | None = Header(default=None, alias="X-ID-Number"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    token_hash = _hash_token(token)

    link = await session.scalar(
        select(StatementDownloadLink).where(
            StatementDownloadLink.token_hash == token_hash
        )
    )

    if not link:
        raise HTTPException(status_code=404, detail="Invalid download link")

    now_utc = datetime.now(UTC)
    if link.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Download link has been revoked")
    if link.expires_at < now_utc:
        raise HTTPException(status_code=410, detail="Download link has expired")
    if link.download_count >= link.max_downloads:
        raise HTTPException(status_code=410, detail="Download limit exceeded")

    statement = await session.get(AccountStatement, link.statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    customer = await session.get(Customer, statement.customer_id)
    if not customer or not customer.id_number_hash:
        raise HTTPException(
            status_code=409,
            detail="Customer ID number is not configured for statement protection",
        )
    if not x_id_number or not verify_secret(x_id_number, customer.id_number_hash):
        raise HTTPException(
            status_code=401, detail="Invalid or missing customer ID number"
        )

    try:
        raw_pdf = storage_service.read_pdf(statement.file_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Statement file is unavailable"
        ) from exc
    protected_pdf = encrypt_pdf_content(raw_pdf, x_id_number)

    link.download_count += 1
    link.last_downloaded_at = now_utc
    await session.commit()

    return Response(
        content=protected_pdf,
        media_type=statement.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{statement.file_name}"',
        },
    )
