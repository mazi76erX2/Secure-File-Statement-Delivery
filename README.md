# Secure File Statement Delivery

Secure FastAPI backend for storing account statement PDFs and issuing time-limited download links. Downloaded PDFs are encrypted with the customer ID number so only the intended customer can open them.

## Core capabilities

- Customer onboarding with hashed ID number storage
- PDF statement upload and metadata tracking
- Pluggable storage backends: local, AWS S3, Azure Blob, MinIO
- One-time or limited-use signed download links
- Time-limited links with revocation and download counters
- ID-based PDF encryption at download time

## Architecture overview

- API layer: `server/api/statements.py`
- Security utilities: `server/security.py`
- Storage abstraction: `server/services/document_storage.py`
- Persistence: SQLAlchemy models in `server/models.py`
- Migrations: Alembic in `alembic/`

### Download security flow

1. Admin uploads a PDF statement for a customer.
2. API stores the document in configured backend and persists metadata.
3. API generates a random token and stores only its hash.
4. Customer calls `/statements/download/{token}` with `X-ID-Number`.
5. API verifies link validity and ID hash.
6. API encrypts PDF bytes with that ID before returning file.

## Prerequisites

- Docker + Docker Compose
- `uv` (for local dev checks)
- OpenTofu/Terraform (optional for infra provisioning)

## Quick start (Docker development)

```bash
cp .env.example .env
docker compose up -d --build
```

API docs: `http://localhost:8000/docs`

Stop:

```bash
docker compose down -v
```

## Production container run

Build production image:

```bash
docker build -f docker/Dockerfile.prod -t secure-statement-api:prod .
```

Run full production compose (API + Postgres + Redis + Nginx):

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d --build
```

Entry endpoint: `http://localhost:1337`

## LGTM observability stack (Docker)

This repository includes a dockerized LGTM stack:

- **Loki** (logs)
- **Grafana** (dashboards)
- **Tempo** (traces)
- **Mimir** (metrics backend)
- **Alloy** (log collection)

Start stack:

```bash
docker compose -f docker-compose.lgtm.yml up -d
```

Access Grafana: `http://localhost:3001` (admin/admin)

Stop stack:

```bash
docker compose -f docker-compose.lgtm.yml down -v
```

## MinIO-backed storage test

Set in `.env`:

```env
STORAGE_PROVIDER=minio
STORAGE_BUCKET_NAME=statements
MINIO_ENDPOINT_URL=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

Then provision bucket via OpenTofu in `infra/terraform/minio`.

## Terraform infrastructure

Terraform modules:

- `infra/terraform/aws`
- `infra/terraform/azure`
- `infra/terraform/minio`

Example:

```bash
cd infra/terraform/minio
tofu init
tofu validate
tofu plan \
  -var='minio_endpoint=http://localhost:9000' \
  -var='minio_access_key=minioadmin' \
  -var='minio_secret_key=minioadmin'
```

For MinIO without KMS, keep `enable_bucket_encryption=false` (default).

## Local quality checks

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy server
uv run pre-commit run --all-files
```

## API endpoints

- `POST /statements/customers`
- `POST /statements/{customer_id}/upload`
- `GET /statements/{customer_id}`
- `POST /statements/{statement_id}/links`
- `POST /statements/{customer_id}/links`
- `GET /statements/download/{token}`

Admin routes require `X-API-Key`. Customer download requires `X-ID-Number`.
