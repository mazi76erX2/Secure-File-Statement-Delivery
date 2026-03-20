"""Generate a password-protected fake statement PDF for local testing."""

from __future__ import annotations

from pathlib import Path

from server.services.statement_pdf_service import StatementPdfService
from server.utils.fake_statement_data import generate_fake_statement_data


def main() -> None:
    id_number = "8001015009087"
    payload = generate_fake_statement_data(transaction_count=100)
    service = StatementPdfService(output_dir=Path("/tmp/statement-output"))

    result = service.create_password_protected_statement(payload, id_number)
    print(f"Created: {result.output_path}")
    print(f"Size: {result.output_path.stat().st_size} bytes")
    print(f"Salt (hex): {result.pdf_salt}")
    print(f"Derived password (hex): {result.pdf_password}")
    print("Password is PBKDF2-derived from the SA ID used in script.")


if __name__ == "__main__":
    main()
