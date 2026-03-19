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
