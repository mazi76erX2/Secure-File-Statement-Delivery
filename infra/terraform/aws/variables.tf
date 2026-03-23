variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "af-south-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment suffix (e.g. prod)"
  default     = "prod"
}

variable "repository_name" {
  type        = string
  description = "Base name for the ECR repository"
  default     = "secure-statement-api"
}

variable "bucket_name" {
  type        = string
  description = "Unique S3 bucket name for statement documents"
}

variable "statement_api_key" {
  type        = string
  description = "Admin API key for statement endpoints"
  sensitive   = true
}

variable "db_password" {
  type        = string
  description = "PostgreSQL admin password"
  sensitive   = true
}

variable "redis_password" {
  type        = string
  description = "Password for internal Redis instance"
  sensitive   = true
}

variable "database_name" {
  type        = string
  description = "Application PostgreSQL database name"
  default     = "secure-file-statement-delivery-app"
}

variable "postgres_admin_username" {
  type        = string
  description = "PostgreSQL admin username"
  default     = "pgadmin"
}

variable "postgres_instance_class" {
  type        = string
  description = "RDS instance class"
  default     = "db.t4g.micro"
}

variable "postgres_storage_gb" {
  type        = number
  description = "PostgreSQL storage allocation in GiB"
  default     = 20
}

variable "postgres_version" {
  type        = string
  description = "PostgreSQL engine version"
  default     = "16.3"
}

variable "redis_node_type" {
  type        = string
  description = "ElastiCache node class"
  default     = "cache.t4g.micro"
}

variable "redis_num_cache_nodes" {
  type        = number
  description = "Number of Redis nodes (cluster mode off requires 1)"
  default     = 1
}

variable "app_image" {
  type        = string
  description = "Override image URI used by the ECS service"
  default     = ""
}

variable "app_image_tag" {
  type        = string
  description = "Fallback image tag that gets appended to the auto-created ECR repository URI"
  default     = "latest"
}

variable "task_cpu" {
  type        = number
  description = "Fargate task CPU units (valid combinations: 256, 512, 1024, 2048, 4096)"
  default     = 512
}

variable "task_memory" {
  type        = number
  description = "Fargate task memory in MiB (must match the chosen CPU configuration)"
  default     = 1024
}

variable "desired_count" {
  type        = number
  description = "Desired number of ECS tasks for the API service"
  default     = 1
}

variable "log_level" {
  type        = string
  description = "Application log level"
  default     = "INFO"
}

variable "pdf_password_kdf_iterations" {
  type        = number
  description = "PBKDF2 iterations for PDF password derivation"
  default     = 600000
}

variable "tags" {
  type        = map(string)
  description = "Tags for all resources"
  default = {
    project = "secure-file-statement-delivery"
  }
}