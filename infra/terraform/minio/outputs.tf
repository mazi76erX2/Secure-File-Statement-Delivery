output "bucket_name" {
  value       = aws_s3_bucket.statements.bucket
  description = "MinIO bucket for statement documents"
}

output "endpoint" {
  value       = var.minio_endpoint
  description = "MinIO S3 endpoint"
}
