output "bucket_name" {
  value       = aws_s3_bucket.statements.bucket
  description = "S3 bucket name"
}

output "bucket_region" {
  value       = var.aws_region
  description = "S3 bucket region"
}
