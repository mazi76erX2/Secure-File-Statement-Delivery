# Terraform Storage Backends

This folder contains Terraform templates for statement document storage backends:

- `aws/` - AWS S3 bucket
- `azure/` - Azure Storage Account + Blob container
- `minio/` - MinIO bucket via S3-compatible AWS provider configuration

## Usage

From one backend folder at a time:

```bash
terraform init
terraform validate
terraform plan -out tfplan
terraform apply tfplan
```

The local environment in this workspace does not currently have Terraform installed (`terraform` command not found).

For macOS, install via Homebrew:

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```
