variable "resource_group_name" {
  type        = string
  description = "Azure resource group name"
}

variable "environment" {
  type        = string
  description = "Deployment environment suffix (e.g. prod)"
  default     = "prod"
}

variable "location" {
  type        = string
  description = "Azure region"
  default     = "southafricanorth"
}

variable "storage_account_name" {
  type        = string
  description = "Globally unique storage account name (3-24 lowercase alphanumeric)"
}

variable "acr_name" {
  type        = string
  description = "Globally unique Azure Container Registry name (5-50 alphanumeric)"
}

variable "key_vault_name" {
  type        = string
  description = "Globally unique Key Vault name"
}

variable "postgres_server_name" {
  type        = string
  description = "Globally unique PostgreSQL Flexible Server name"
}

variable "redis_container_app_name" {
  type        = string
  description = "Container App name for internal Redis service"
  default     = "ca-redis"
}

variable "log_analytics_workspace_name" {
  type        = string
  description = "Log Analytics workspace name"
}

variable "container_app_environment_name" {
  type        = string
  description = "Container Apps environment name"
}

variable "container_app_name" {
  type        = string
  description = "Container App name for API service"
}

variable "container_name" {
  type        = string
  description = "Blob container for statements"
  default     = "statements"
}

variable "app_image" {
  type        = string
  description = "Container image to deploy to Container Apps"
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
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

variable "postgres_sku_name" {
  type        = string
  description = "PostgreSQL Flexible Server SKU"
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  type        = number
  description = "PostgreSQL storage in MB"
  default     = 32768
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
  description = "Password for internal Redis service"
  sensitive   = true
}

variable "pdf_password_kdf_iterations" {
  type        = number
  description = "PBKDF2 iterations for PDF password derivation"
  default     = 600000
}

variable "container_cpu" {
  type        = number
  description = "CPU allocated to the API container"
  default     = 0.5
}

variable "container_memory" {
  type        = string
  description = "Memory allocated to the API container"
  default     = "1Gi"
}

variable "min_replicas" {
  type        = number
  description = "Minimum API replicas for Container Apps"
  default     = 1
}

variable "max_replicas" {
  type        = number
  description = "Maximum API replicas for Container Apps"
  default     = 3
}

variable "log_level" {
  type        = string
  description = "Application log level"
  default     = "INFO"
}

variable "tags" {
  type        = map(string)
  description = "Tags for Azure resources"
  default = {
    project = "secure-file-statement-delivery"
  }
}
