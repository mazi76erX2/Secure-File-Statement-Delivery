from pathlib import Path

from services.statement_pdf_service import (
    PasswordProtectedStatementResult,
    StatementPdfService,
)
from utils.statement_pdf import StatementDocumentData, StatementTransaction


def _payload() -> StatementDocumentData:
    return StatementDocumentData(
        title="Savings Account Statement",
        bank_name="Capitec Bank",
        statement_date="20/03/2026",
        branch="123456",
        device="1234",
        from_date="01/03/2026",
        to_date="20/03/2026",
        print_date="20/03/2026",
        customer_name="TEST USER",
        address_line_1="123 TEST ST",
        address_line_2="CAPE TOWN",
        address_line_3="WESTERN CAPE",
        postal_code="8000",
        account_number="1234567890",
        available_balance="1 234.56",
        transactions=[
            StatementTransaction(
                posting_date="02/03/2026",
                transaction_date="02/03/2026",
                description="Salary",
                money_in="2 000.00",
                balance="3 000.00",
            )
        ],
    )


def test_create_password_protected_statement_returns_metadata(tmp_path: Path) -> None:
    service = StatementPdfService(output_dir=tmp_path)

    result = service.create_password_protected_statement(_payload(), "8001015009087")

    assert isinstance(result, PasswordProtectedStatementResult)
    assert result.output_path.exists()
    assert result.output_path.stat().st_size > 0
    assert len(result.pdf_salt) == 64
    assert len(result.pdf_password) == 64


def test_create_password_protected_statement_rejects_invalid_sa_id(
    tmp_path: Path,
) -> None:
    service = StatementPdfService(output_dir=tmp_path)

    try:
        service.create_password_protected_statement(_payload(), "123")
        raise AssertionError("Expected ValueError for invalid SA ID")
    except ValueError as exc:
        assert str(exc) == "Invalid South African ID number"
