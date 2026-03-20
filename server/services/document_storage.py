"""Pluggable document storage service for local, AWS S3, Azure Blob, and MinIO."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, TypedDict, cast


class _S3BodyReader(Protocol):
    def read(self) -> bytes: ...


class _S3GetObjectResponse(TypedDict):
    Body: _S3BodyReader


class _S3Client(Protocol):
    def put_object(
        self, *, Bucket: str, Key: str, Body: bytes, ContentType: str
    ) -> object: ...

    def get_object(self, *, Bucket: str, Key: str) -> _S3GetObjectResponse: ...


class _AzureBlobDownloader(Protocol):
    def readall(self) -> bytes: ...


class _AzureBlobClient(Protocol):
    def download_blob(self) -> _AzureBlobDownloader: ...


class _AzureBlobContainerClient(Protocol):
    def upload_blob(self, *, name: str, data: bytes, overwrite: bool) -> object: ...

    def get_blob_client(self, blob: str) -> _AzureBlobClient: ...


class StorageConfigurationError(ValueError):
    """Raised when the storage backend is misconfigured."""


class StorageUnavailableError(RuntimeError):
    """Raised when the storage backend is unavailable."""


class DocumentStorageService:
    def __init__(self, settings: object) -> None:
        self.settings = settings
        self.provider = str(getattr(settings, "storage_provider", "local")).lower()
        self.prefix = str(getattr(settings, "storage_prefix", "statements")).strip("/")

        self._s3_client: _S3Client | None = None
        self._blob_container_client: _AzureBlobContainerClient | None = None

    def save_pdf(self, content: bytes, customer_id: int, file_name: str) -> str:
        object_key = self._build_object_key(customer_id, file_name)

        if self.provider == "local":
            full_path = self._resolve_local_path(object_key)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                full_path.write_bytes(content)
            except OSError as exc:
                raise StorageUnavailableError(
                    "Failed to write statement to local storage"
                ) from exc
            return object_key

        if self.provider in {"aws", "minio"}:
            from botocore.exceptions import BotoCoreError, ClientError

            bucket = self._require_setting("storage_bucket_name")
            client = self._get_s3_client()
            try:
                client.put_object(
                    Bucket=bucket,
                    Key=object_key,
                    Body=content,
                    ContentType="application/pdf",
                )
            except (ClientError, BotoCoreError) as exc:
                raise StorageUnavailableError(
                    "Failed to store statement in S3-compatible backend"
                ) from exc
            return object_key

        if self.provider == "azure":
            from azure.core.exceptions import AzureError

            blob_client = self._get_blob_container_client()
            try:
                blob_client.upload_blob(name=object_key, data=content, overwrite=True)
            except AzureError as exc:
                raise StorageUnavailableError(
                    "Failed to store statement in Azure Blob storage"
                ) from exc
            return object_key

        raise StorageConfigurationError(
            f"Unsupported storage_provider: {self.provider}"
        )

    def read_pdf(self, object_key: str) -> bytes:
        if self.provider == "local":
            path = self._resolve_local_path(object_key)
            if not path.exists() or not path.is_file():
                raise FileNotFoundError("Statement file is unavailable")
            try:
                return path.read_bytes()
            except OSError as exc:
                raise StorageUnavailableError(
                    "Failed to read statement from local storage"
                ) from exc

        if self.provider in {"aws", "minio"}:
            from botocore.exceptions import BotoCoreError, ClientError

            bucket = self._require_setting("storage_bucket_name")
            client = self._get_s3_client()
            try:
                response = client.get_object(Bucket=bucket, Key=object_key)
            except ClientError as exc:
                error_code = (
                    exc.response.get("Error", {}).get("Code")
                    if hasattr(exc, "response")
                    else None
                )
                if error_code in {"404", "NoSuchKey", "NotFound"}:
                    raise FileNotFoundError("Statement file is unavailable") from exc
                raise StorageUnavailableError(
                    "Failed to read statement from S3-compatible backend"
                ) from exc
            except BotoCoreError as exc:
                raise StorageUnavailableError(
                    "Failed to read statement from S3-compatible backend"
                ) from exc
            return response["Body"].read()

        if self.provider == "azure":
            from azure.core.exceptions import AzureError, ResourceNotFoundError

            blob_client = self._get_blob_container_client().get_blob_client(object_key)
            try:
                return blob_client.download_blob().readall()
            except ResourceNotFoundError as exc:
                raise FileNotFoundError("Statement file is unavailable") from exc
            except AzureError as exc:
                raise StorageUnavailableError(
                    "Failed to read statement from Azure Blob storage"
                ) from exc

        raise StorageConfigurationError(
            f"Unsupported storage_provider: {self.provider}"
        )

    def _build_object_key(self, customer_id: int, file_name: str) -> str:
        safe_name = Path(file_name or "statement.pdf").name
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        key = f"{customer_id}/{timestamp}_{safe_name}"
        return f"{self.prefix}/{key}" if self.prefix else key

    def _require_setting(self, key: str) -> str:
        value = getattr(self.settings, key, None)
        if not value:
            raise StorageConfigurationError(f"Missing required setting: {key}")
        return str(value)

    def _local_base_dir(self) -> Path:
        return Path(
            getattr(self.settings, "statement_storage_dir", "storage/statements")
        ).resolve()

    def _resolve_local_path(self, object_key: str) -> Path:
        base_dir = self._local_base_dir()
        candidate = (base_dir / object_key).resolve()
        try:
            candidate.relative_to(base_dir)
        except ValueError as exc:
            raise FileNotFoundError("Statement file is unavailable") from exc
        return candidate

    def _get_s3_client(self) -> _S3Client:
        if self._s3_client is not None:
            return self._s3_client

        import boto3

        if self.provider == "aws":
            self._s3_client = cast(
                _S3Client,
                boto3.client(
                    "s3",
                    region_name=getattr(self.settings, "aws_region", None),
                    aws_access_key_id=getattr(self.settings, "aws_access_key_id", None),
                    aws_secret_access_key=getattr(
                        self.settings, "aws_secret_access_key", None
                    ),
                ),
            )
            return self._s3_client

        self._s3_client = cast(
            _S3Client,
            boto3.client(
                "s3",
                endpoint_url=self._require_setting("minio_endpoint_url"),
                aws_access_key_id=self._require_setting("minio_access_key"),
                aws_secret_access_key=self._require_setting("minio_secret_key"),
                use_ssl=bool(getattr(self.settings, "minio_secure", True)),
                region_name=getattr(self.settings, "aws_region", "us-east-1"),
            ),
        )
        return self._s3_client

    def _get_blob_container_client(self) -> _AzureBlobContainerClient:
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
        self._blob_container_client = cast(
            _AzureBlobContainerClient, service.get_container_client(container)
        )
        return self._blob_container_client
