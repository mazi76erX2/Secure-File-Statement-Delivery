variable "resource_group_name" {
  type        = string
  description = "Azure resource group name"
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

variable "container_name" {
  type        = string
  description = "Blob container for statements"
  default     = "statements"
}

variable "tags" {
  type        = map(string)
  description = "Tags for Azure resources"
  default = {
    project = "secure-file-statement-delivery"
  }
}
