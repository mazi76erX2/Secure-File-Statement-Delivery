"""Pluggable document storage service for local, AWS S3, Azure Blob, and MinIO."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class DocumentStorageService:
    def __init__(self, settings: object) -> None:
        self.settings = settings
        self.provider = str(getattr(settings, "storage_provider", "local")).lower()
        self.prefix = str(getattr(settings, "storage_prefix", "statements")).strip("/")

        self._s3_client: Any | None = None
        self._blob_container_client: Any | None = None

    def save_pdf(self, content: bytes, customer_id: int, file_name: str) -> str:
        object_key = self._build_object_key(customer_id, file_name)

        if self.provider == "local":
            base_dir = Path(
                getattr(self.settings, "statement_storage_dir", "storage/statements")
            )
            full_path = base_dir / object_key
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)
            return object_key

        if self.provider in {"aws", "minio"}:
            bucket = self._require_setting("storage_bucket_name")
            client = self._get_s3_client()
            client.put_object(
                Bucket=bucket,
                Key=object_key,
                Body=content,
                ContentType="application/pdf",
            )
            return object_key

        if self.provider == "azure":
            blob_client = self._get_blob_container_client()
            blob_client.upload_blob(name=object_key, data=content, overwrite=True)
            return object_key

        raise ValueError(f"Unsupported storage_provider: {self.provider}")

    def read_pdf(self, object_key: str) -> bytes:
        if self.provider == "local":
            base_dir = Path(
                getattr(self.settings, "statement_storage_dir", "storage/statements")
            )
            path = base_dir / object_key
            if not path.exists() or not path.is_file():
                raise FileNotFoundError("Statement file is unavailable")
            return path.read_bytes()

        if self.provider in {"aws", "minio"}:
            bucket = self._require_setting("storage_bucket_name")
            client = self._get_s3_client()
            response = client.get_object(Bucket=bucket, Key=object_key)
            return response["Body"].read()

        if self.provider == "azure":
            blob_client = self._get_blob_container_client().get_blob_client(object_key)
            return blob_client.download_blob().readall()

        raise ValueError(f"Unsupported storage_provider: {self.provider}")

    def _build_object_key(self, customer_id: int, file_name: str) -> str:
        safe_name = Path(file_name or "statement.pdf").name
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        key = f"{customer_id}/{timestamp}_{safe_name}"
        return f"{self.prefix}/{key}" if self.prefix else key

    def _require_setting(self, key: str) -> str:
        value = getattr(self.settings, key, None)
        if not value:
            raise ValueError(f"Missing required setting: {key}")
        return str(value)

    def _get_s3_client(self):
        if self._s3_client is not None:
            return self._s3_client

        import boto3

        if self.provider == "aws":
            self._s3_client = boto3.client(
                "s3",
                region_name=getattr(self.settings, "aws_region", None),
                aws_access_key_id=getattr(self.settings, "aws_access_key_id", None),
                aws_secret_access_key=getattr(
                    self.settings, "aws_secret_access_key", None
                ),
            )
            return self._s3_client

        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self._require_setting("minio_endpoint_url"),
            aws_access_key_id=self._require_setting("minio_access_key"),
            aws_secret_access_key=self._require_setting("minio_secret_key"),
            use_ssl=bool(getattr(self.settings, "minio_secure", True)),
            region_name=getattr(self.settings, "aws_region", "us-east-1"),
        )
        return self._s3_client

    def _get_blob_container_client(self):
        if self._blob_container_client is not None:
            return self._blob_container_client

        from azure.storage.blob import BlobServiceClient

        connection_string = getattr(
            self.settings, "azure_storage_connection_string", None
        )
        if connection_string:
            service = BlobServiceClient.from_connection_string(str(connection_string))
        else:
            account_url = self._require_setting("azure_storage_account_url")
            account_key = self._require_setting("azure_storage_account_key")
            service = BlobServiceClient(account_url=account_url, credential=account_key)

        container = self._require_setting("azure_storage_container")
        self._blob_container_client = service.get_container_client(container)
        return self._blob_container_client
