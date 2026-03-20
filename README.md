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

## API Usage Examples

All admin endpoints require the `X-API-Key` header. The download endpoint requires `X-ID-Number`.

### 1. Create a Customer

```bash
curl -X POST http://localhost:8000/statements/customers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $STATEMENT_API_KEY" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "id_number": "1234567890"
  }'
```

Response:

```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "john@example.com",
  "id_number_configured": true,
  "created_at": "2026-03-19T12:00:00Z",
  "updated_at": "2026-03-19T12:00:00Z"
}
```

### 2. Upload a Statement PDF

```bash
curl -X POST http://localhost:8000/statements/1/upload \
  -H "X-API-Key: $STATEMENT_API_KEY" \
  -F "account_number_last4=1234" \
  -F "statement_period_start=2026-01-01" \
  -F "statement_period_end=2026-01-31" \
  -F "file=@january-statement.pdf"
```

Response:

```json
{
  "id": 1,
  "customer_id": 1,
  "account_number_last4": "1234",
  "statement_period_start": "2026-01-01",
  "statement_period_end": "2026-01-31",
  "file_name": "january-statement.pdf",
  "file_path": "statements/1/2026/01/january-statement.pdf",
  "content_type": "application/pdf",
  "file_size_bytes": 102400,
  "checksum_sha256": "abc123...",
  "created_at": "2026-03-19T12:05:00Z"
}
```

### 3. List Customer Statements

```bash
# List all statements for customer (defaults to previous month)
curl -X GET http://localhost:8000/statements/1 \
  -H "X-API-Key: $STATEMENT_API_KEY"

# Filter by month range
curl -X GET "http://localhost:8000/statements/1?from_month=2026-01&to_month=2026-03" \
  -H "X-API-Key: $STATEMENT_API_KEY"
```

### 4. Issue a Download Link

```bash
# For a single statement
curl -X POST http://localhost:8000/statements/1/links \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $STATEMENT_API_KEY" \
  -d '{
    "expires_in_seconds": 3600,
    "max_downloads": 3
  }'
```

Response:

```json
{
  "id": 1,
  "statement_id": 1,
  "expires_at": "2026-03-19T13:05:00Z",
  "max_downloads": 3,
  "download_count": 0,
  "token": "secure-random-token-here",
  "download_url": "http://localhost:8000/statements/download/secure-random-token-here"
}
```

### 5. Download Statement (Customer)

The customer uses the `X-ID-Number` header with their ID number to decrypt the PDF:

```bash
curl -X GET "http://localhost:8000/statements/download/secure-random-token-here" \
  -H "X-ID-Number: 1234567890" \
  --output my-statement.pdf
```

The returned PDF is encrypted with the customer's ID number as the password.

## API Endpoints Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/statements/customers` | X-API-Key | Create customer |
| POST | `/statements/{customer_id}/upload` | X-API-Key | Upload PDF statement |
| GET | `/statements/{customer_id}` | X-API-Key | List customer statements |
| POST | `/statements/{statement_id}/links` | X-API-Key | Issue download link |
| POST | `/statements/{customer_id}/links` | X-API-Key | Issue links for month range |
| GET | `/statements/download/{token}` | X-ID-Number | Download encrypted PDF |

## Testing

### Run Unit Tests

```bash
# Install dependencies
uv sync --all-extras

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=server --cov-report=html
# View report at: htmlcov/index.html

# Run integration tests only
uv run pytest -m integration
```

### End-to-End Docker Test

```bash
# Start services
docker compose up -d --build

# Wait for healthy startup
sleep 5

# Test API is responding
curl http://localhost:8000/docs

# Create a customer
curl -X POST http://localhost:8000/statements/customers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-this-to-a-long-random-value" \
  -d '{"full_name": "Test User", "email": "test@example.com", "id_number": "123456"}'

# Clean up
docker compose down -v
```

## Local Development Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker + Docker Compose
- PostgreSQL (or use Docker)
- Redis (or use Docker)

### Setup Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd Secure-File-Statement-Delivery

# 2. Install dependencies
uv sync --all-extras

# 3. Copy environment file
cp .env.example .env

# 4. Start database and cache (Docker)
docker compose up -d db redis

# 5. Run database migrations
uv run alembic upgrade head

# 6. Start the development server
uv run uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Pre-commit Hooks

```bash
# Install hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| **Database** | | |
| `DATABASE_NAME` | - | PostgreSQL database name |
| `DATABASE_USERNAME` | `postgres` | Database username |
| `DATABASE_PASSWORD` | - | Database password |
| `DATABASE_HOST` | `db` | Database hostname |
| `DATABASE_PORT` | `5432` | Database port |
| **Cache** | | |
| `CACHE_HOST` | `redis` | Redis hostname |
| `CACHE_PORT` | `6379` | Redis port |
| `CACHE_DB` | `0` | Redis database number |
| **Storage** | | |
| `STORAGE_PROVIDER` | `local` | Backend: `local`, `aws`, `azure`, `minio` |
| `STORAGE_BUCKET_NAME` | - | S3/Azure/MinIO bucket name |
| `STORAGE_PREFIX` | `statements` | Object key prefix |
| `STATEMENT_STORAGE_DIR` | `storage/statements` | Local storage directory |
| **AWS S3** | | |
| `AWS_REGION` | `af-south-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key |
| **Azure Blob** | | |
| `AZURE_STORAGE_CONNECTION_STRING` | - | Connection string |
| `AZURE_STORAGE_ACCOUNT_URL` | - | Account URL |
| `AZURE_STORAGE_ACCOUNT_KEY` | - | Account key |
| `AZURE_STORAGE_CONTAINER` | `statements` | Container name |
| **MinIO** | | |
| `MINIO_ENDPOINT_URL` | `http://localhost:9000` | MinIO endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_SECURE` | `false` | Use HTTPS |
| **Runtime** | | |
| `DEBUG` | `true` | Debug mode |
| `FASTAPI_ENV` | `dev` | Environment: `dev`, `prod` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ALLOW_ORIGINS` | - | Comma-separated allowed origins |
| `MAX_STATEMENT_FILE_SIZE_BYTES` | `10485760` | Maximum upload size in bytes |
| `STATEMENT_DOWNLOAD_RATE_LIMIT_REQUESTS` | `10` | Max download attempts per client IP per window |
| `STATEMENT_DOWNLOAD_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window size in seconds |
| `TRUST_PROXY_HEADERS` | `false` | Trust `X-Forwarded-For` for client IP extraction |
| `STATEMENT_API_KEY` | - | API key for admin endpoints |

## AWS Deployment Guide

### Prerequisites

- AWS CLI configured with credentials
- Terraform/OpenTofu installed
- ECR repository created

### 1. Build and Push Docker Image

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region af-south-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.af-south-1.amazonaws.com

# Build production image
docker build -f docker/Dockerfile.prod -t secure-statement-api:prod .

# Tag and push
docker tag secure-statement-api:prod <account-id>.dkr.ecr.af-south-1.amazonaws.com/secure-statement-api:latest
docker push <account-id>.dkr.ecr.af-south-1.amazonaws.com/secure-statement-api:latest
```

### 2. Provision Infrastructure

```bash
cd infra/terraform/aws

# Initialize Terraform
terraform init

# Review plan
terraform plan \
  -var="environment=prod" \
  -var="aws_region=af-south-1" \
  -var="bucket_name=my-statements-bucket"

# Apply
terraform apply \
  -var="environment=prod" \
  -var="aws_region=af-south-1" \
  -var="bucket_name=my-statements-bucket"
```

### 3. Deploy to EKS (GitOps)

For EKS deployment with ArgoCD:

1. Create Kubernetes manifests in `infra/k8s/`
2. Configure ArgoCD Application pointing to the repo
3. Push changes to trigger deployment

### AWS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           AWS Cloud                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │     ALB      │───▶│     EKS      │───▶│   RDS Postgres   │  │
│  │ (Ingress)    │    │  (FastAPI)   │    │                  │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│                      ┌──────────────┐    ┌──────────────────┐  │
│                      │ ElastiCache  │    │        S3        │  │
│                      │   (Redis)    │    │   (Statements)   │  │
│                      └──────────────┘    └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## CI/CD Pipeline

The repository includes GitHub Actions workflows for continuous integration.

### Workflow: Format and Lint

**Triggers:** Push/PR to `main` or `master`

**Steps:**

1. Checkout code
2. Install uv package manager
3. Setup Python 3.14
4. Install dependencies (`uv sync --all-extras`)
5. Format check (`ruff format --check .`)
6. Lint (`ruff check .`)
7. Type check (`mypy server`)

### Running CI Checks Locally

```bash
# Run all checks (same as CI)
uv run ruff format --check .
uv run ruff check .
uv run mypy server
```

## Troubleshooting

### Container Startup Issues

**Problem:** Backend fails to connect to database

```
Connection refused: db:5432
```

**Solution:** The entrypoint waits for DNS resolution and port availability. If issues persist:

```bash
# Check container logs
docker compose logs backend

# Verify database is healthy
docker compose ps

# Restart with fresh volumes
docker compose down -v && docker compose up -d
```

### MinIO Encryption Errors

**Problem:** Terraform fails with "NotImplemented" on bucket encryption

```
Error: error putting S3 Bucket Server Side Encryption: NotImplemented
```

**Solution:** MinIO without KMS doesn't support SSE. Set:

```hcl
enable_bucket_encryption = false  # default
```

### PDF Download Fails

**Problem:** 401 or 410 errors when downloading

**Possible causes:**

1. **401 - Invalid ID number:** Verify `X-ID-Number` header matches customer's ID
2. **410 - Link expired:** Token has expired or max downloads reached
3. **404 - Invalid token:** Token doesn't exist or was revoked

```bash
# Check link status (admin)
curl http://localhost:8000/statements/{customer_id} \
  -H "X-API-Key: $STATEMENT_API_KEY"
```

### LGTM Stack Issues

**Problem:** Loki fails to start

```
permission denied: /loki/wal
```

**Solution:** Fixed in `loki.yml`. If persisting, ensure volumes are clean:

```bash
docker compose -f docker-compose.lgtm.yml down -v
docker compose -f docker-compose.lgtm.yml up -d
```

### Database Migration Errors

**Problem:** Alembic migration fails

```bash
# Check current revision
uv run alembic current

# Show migration history
uv run alembic history

# Downgrade if needed
uv run alembic downgrade -1

# Re-run upgrade
uv run alembic upgrade head
```

## License

MIT
