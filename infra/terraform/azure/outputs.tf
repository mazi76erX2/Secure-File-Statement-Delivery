output "storage_account_name" {
  value       = azurerm_storage_account.statements.name
  description = "Azure Storage account name"
}

output "storage_account_primary_blob_endpoint" {
  value       = azurerm_storage_account.statements.primary_blob_endpoint
  description = "Primary Blob endpoint URL"
}

output "container_name" {
  value       = azurerm_storage_container.statements.name
  description = "Blob container for statement documents"
}

output "acr_login_server" {
  value       = azurerm_container_registry.main.login_server
  description = "ACR login server"
}

output "container_app_url" {
  value       = "https://${azurerm_container_app.api.latest_revision_fqdn}"
  description = "Public URL for the API Container App"
}

output "container_app_fqdn" {
  value       = azurerm_container_app.api.latest_revision_fqdn
  description = "Container App latest revision FQDN"
}

output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.main.fqdn
  description = "PostgreSQL Flexible Server hostname"
}

output "redis_hostname" {
  value       = azurerm_redis_cache.main.hostname
  description = "Azure Redis hostname"
}

output "redis_ssl_port" {
  value       = azurerm_redis_cache.main.ssl_port
  description = "Azure Redis SSL port"
}

output "key_vault_name" {
  value       = azurerm_key_vault.main.name
  description = "Key Vault used for deployment secrets"
}

output "blob_connection_string" {
  value       = azurerm_storage_account.statements.primary_connection_string
  description = "Blob storage connection string"
  sensitive   = true
}
