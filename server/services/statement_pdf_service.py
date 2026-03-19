"""Service for creating password-protected account statement PDFs."""

from __future__ import annotations

from pathlib import Path

try:
    from security import encrypt_pdf_content
    from utils.sa_id import validate_sa_id
    from utils.statement_pdf import AccountStatementPdf, StatementDocumentData
except ImportError:  # pragma: no cover
    from server.security import encrypt_pdf_content
    from server.utils.sa_id import validate_sa_id
    from server.utils.statement_pdf import AccountStatementPdf, StatementDocumentData


class StatementPdfService:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_password_protected_statement(
        self,
        payload: StatementDocumentData,
        id_number: str,
    ) -> Path:
        if not validate_sa_id(id_number):
            raise ValueError("Invalid South African ID number")

        generator = AccountStatementPdf()
        raw_pdf = generator.render(payload)
        encrypted_pdf = encrypt_pdf_content(raw_pdf, id_number)

        output_path = self.output_dir / "account_statement.pdf"
        output_path.write_bytes(encrypted_pdf)
        return output_path
