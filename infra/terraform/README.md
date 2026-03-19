# Terraform Storage Backends

This folder contains Terraform/OpenTofu templates for statement document storage backends:

- `aws/` - AWS S3 bucket
- `azure/` - Azure Storage Account + Blob container
- `minio/` - MinIO bucket via S3-compatible AWS provider configuration

## Usage

Run from one backend folder at a time:

```bash
tofu init
tofu validate
tofu plan -out tfplan
tofu apply tfplan
```

Terraform works too if preferred (`terraform` instead of `tofu`).

## MinIO notes

The MinIO module includes:

- bucket creation
- bucket versioning
- optional SSE configuration via `enable_bucket_encryption`

`enable_bucket_encryption` defaults to `false` because many local/dev MinIO setups do not have KMS configured.
