provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "statements" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_storage_account" "statements" {
  name                            = var.storage_account_name
  resource_group_name             = azurerm_resource_group.statements.name
  location                        = azurerm_resource_group.statements.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = true
  tags                            = var.tags
}

resource "azurerm_storage_container" "statements" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.statements.id
  container_access_type = "private"
}
