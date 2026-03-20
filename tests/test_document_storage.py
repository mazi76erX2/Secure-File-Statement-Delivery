from pathlib import Path

import pytest
from services.document_storage import DocumentStorageService


class _Settings:
    storage_provider = "local"
    storage_prefix = "statements"
    statement_storage_dir = ""


def _service(tmp_path: Path) -> DocumentStorageService:
    settings = _Settings()
    settings.statement_storage_dir = str(tmp_path)
    return DocumentStorageService(settings)


def test_local_storage_round_trip(tmp_path: Path) -> None:
    service = _service(tmp_path)
    content = b"%PDF-1.4\n..."

    object_key = service.save_pdf(content, customer_id=7, file_name="statement.pdf")
    loaded = service.read_pdf(object_key)

    assert loaded == content


def test_local_storage_rejects_traversal_read(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(FileNotFoundError):
        service.read_pdf("../outside.txt")
