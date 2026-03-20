"""Service for creating password-protected account statement PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from security import derive_pdf_password, encrypt_pdf_content, generate_pdf_salt
    from utils.sa_id import validate_sa_id
    from utils.statement_pdf import AccountStatementPdf, StatementDocumentData
except ImportError:  # pragma: no cover
    from server.security import (
        derive_pdf_password,
        encrypt_pdf_content,
        generate_pdf_salt,
    )
    from server.utils.sa_id import validate_sa_id
    from server.utils.statement_pdf import AccountStatementPdf, StatementDocumentData


@dataclass(slots=True)
class PasswordProtectedStatementResult:
    output_path: Path
    pdf_password: str
    pdf_salt: str


class StatementPdfService:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_password_protected_statement(
        self,
        payload: StatementDocumentData,
        id_number: str,
    ) -> PasswordProtectedStatementResult:
        if not validate_sa_id(id_number):
            raise ValueError("Invalid South African ID number")

        generator = AccountStatementPdf()
        raw_pdf = generator.render(payload)
        pdf_salt = generate_pdf_salt()
        pdf_password = derive_pdf_password(id_number, pdf_salt)
        encrypted_pdf = encrypt_pdf_content(raw_pdf, pdf_password)

        output_path = self.output_dir / "account_statement.pdf"
        output_path.write_bytes(encrypted_pdf)
        return PasswordProtectedStatementResult(
            output_path=output_path,
            pdf_password=pdf_password,
            pdf_salt=pdf_salt,
        )
