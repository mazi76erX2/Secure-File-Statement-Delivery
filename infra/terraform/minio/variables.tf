variable "bucket_name" {
  type        = string
  description = "MinIO bucket name"
  default     = "statements"
}

variable "minio_endpoint" {
  type        = string
  description = "MinIO S3 endpoint, e.g. http://localhost:9000"
}

variable "minio_access_key" {
  type        = string
  description = "MinIO access key"
}

variable "minio_secret_key" {
  type        = string
  description = "MinIO secret key"
  sensitive   = true
}

variable "region" {
  type        = string
  description = "Pseudo-region for S3-compatible provider"
  default     = "us-east-1"
}

variable "enable_bucket_encryption" {
  type        = bool
  description = "Enable bucket default encryption (requires MinIO KMS configuration)"
  default     = false
}
