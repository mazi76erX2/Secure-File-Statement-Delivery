output "bucket_name" {
  value       = aws_s3_bucket.statements.bucket
  description = "S3 bucket name"
}

output "bucket_region" {
  value       = var.aws_region
  description = "S3 bucket region"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.api.repository_url
  description = "ECR repository that holds the API image"
}

output "ecs_service_url" {
  value       = "http://${aws_lb.api.dns_name}"
  description = "Public URL for the ECS service fronted by the ALB"
}

output "postgres_endpoint" {
  value       = aws_db_instance.main.address
  description = "PostgreSQL instance endpoint"
}

output "redis_endpoint" {
  value       = format("%s:%s", aws_elasticache_cluster.redis.cache_nodes[0].address, aws_elasticache_cluster.redis.cache_nodes[0].port)
  description = "ElastiCache Redis endpoint"
}