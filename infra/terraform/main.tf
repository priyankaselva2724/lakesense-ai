# Azure data lake foundation (Tier B). Nothing here is applied until YOU run `terraform apply`.
terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 3.100" }
  }
}

provider "azurerm" {
  features {}
}

variable "location" {
  type    = string
  default = "centralindia"
}

variable "prefix" {
  type        = string
  description = "Short lowercase prefix (letters and digits) used to build globally unique names"
}

resource "azurerm_resource_group" "rg" {
  name     = "${var.prefix}-lakesense-rg"
  location = var.location
}

# ADLS Gen2 storage account = the Azure equivalent of the local MinIO bucket
resource "azurerm_storage_account" "lake" {
  name                     = "${var.prefix}lakesense"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_data_lake_gen2_filesystem" "bronze" {
  name               = "bronze"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "silver" {
  name               = "silver"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "gold" {
  name               = "gold"
  storage_account_id = azurerm_storage_account.lake.id
}

output "storage_account" { value = azurerm_storage_account.lake.name }
output "dfs_endpoint" { value = azurerm_storage_account.lake.primary_dfs_endpoint }
