provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "statements" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

data "azurerm_client_config" "current" {}

resource "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.statements.name
  location            = azurerm_resource_group.statements.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.tags
}

resource "azurerm_key_vault" "main" {
  name                        = var.key_vault_name
  resource_group_name         = azurerm_resource_group.statements.name
  location                    = azurerm_resource_group.statements.location
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  purge_protection_enabled    = false
  soft_delete_retention_days  = 7
  enabled_for_disk_encryption = false
  tags                        = var.tags
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = ["Get", "Set", "List", "Delete"]
}

resource "azurerm_key_vault_secret" "statement_api_key" {
  name         = "statement-api-key"
  value        = var.statement_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_key_vault_access_policy.deployer]
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = var.db_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_key_vault_access_policy.deployer]
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

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = var.postgres_server_name
  resource_group_name    = azurerm_resource_group.statements.name
  location               = azurerm_resource_group.statements.location
  version                = "16"
  administrator_login    = var.postgres_admin_username
  administrator_password = var.db_password
  storage_mb             = var.postgres_storage_mb
  sku_name               = var.postgres_sku_name
  tags                   = var.tags

  authentication {
    active_directory_auth_enabled = false
    password_auth_enabled         = true
  }
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = var.log_analytics_workspace_name
  location            = azurerm_resource_group.statements.location
  resource_group_name = azurerm_resource_group.statements.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = var.container_app_environment_name
  location                   = azurerm_resource_group.statements.location
  resource_group_name        = azurerm_resource_group.statements.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = var.tags
}

resource "azurerm_container_app" "redis" {
  name                         = var.redis_container_app_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.statements.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = var.tags

  ingress {
    external_enabled = false
    target_port      = 6379
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "redis"
      image  = "redis:8.6.1-alpine"
      cpu    = 0.25
      memory = "0.5Gi"
      args   = ["redis-server", "--requirepass", var.redis_password]
    }
  }
}

resource "azurerm_container_app" "api" {
  name                         = var.container_app_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.statements.name
  revision_mode                = "Single"
  tags                         = var.tags

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  secret {
    name  = "statement-api-key"
    value = var.statement_api_key
  }

  secret {
    name  = "db-password"
    value = var.db_password
  }

  secret {
    name  = "redis-password"
    value = var.redis_password
  }

  secret {
    name  = "azure-storage-connection-string"
    value = azurerm_storage_account.statements.primary_connection_string
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 8000
    transport                  = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "api"
      image  = var.app_image
      cpu    = var.container_cpu
      memory = var.container_memory

      env {
        name  = "FASTAPI_ENV"
        value = var.environment
      }

      env {
        name  = "DEBUG"
        value = "false"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name  = "DATABASE_HOST"
        value = azurerm_postgresql_flexible_server.main.fqdn
      }

      env {
        name  = "DATABASE_PORT"
        value = "5432"
      }

      env {
        name  = "DATABASE_NAME"
        value = azurerm_postgresql_flexible_server_database.app.name
      }

      env {
        name  = "DATABASE_USERNAME"
        value = var.postgres_admin_username
      }

      env {
        name        = "DATABASE_PASSWORD"
        secret_name = "db-password"
      }

      env {
        name  = "DATABASE_SSL_MODE"
        value = "require"
      }

      env {
        name  = "CACHE_HOST"
        value = var.redis_container_app_name
      }

      env {
        name  = "CACHE_PORT"
        value = "6379"
      }

      env {
        name  = "CACHE_DB"
        value = "0"
      }

      env {
        name  = "CACHE_USE_SSL"
        value = "false"
      }

      env {
        name  = "CACHE_SSL_CERT_REQS"
        value = "none"
      }

      env {
        name        = "CACHE_PASSWORD"
        secret_name = "redis-password"
      }

      env {
        name  = "STORAGE_PROVIDER"
        value = "azure"
      }

      env {
        name        = "AZURE_STORAGE_CONNECTION_STRING"
        secret_name = "azure-storage-connection-string"
      }

      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = azurerm_storage_container.statements.name
      }

      env {
        name        = "STATEMENT_API_KEY"
        secret_name = "statement-api-key"
      }

      env {
        name  = "PDF_PASSWORD_KDF_ITERATIONS"
        value = tostring(var.pdf_password_kdf_iterations)
      }
    }
  }
}
