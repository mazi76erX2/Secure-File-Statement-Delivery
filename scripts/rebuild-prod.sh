#!/usr/bin/env bash
set -euo pipefail

SUBSCRIPTION_ID="563e3a21-bb51-4f11-a4ed-b3124b09f5e8"
LOCATION="southafricanorth"

STATE_RG="rg-tfstate"
STATE_SA="tfstatemazi"
STATE_CONTAINER="tfstate"

APP_RG="rg-mazistmtprod"
KEY_VAULT_NAME="kv-mazistmtprod-01"
REPO="mazi76erX2/Secure-File-Statement-Delivery"
WORKFLOW="deploy-azure-prod.yml"

AZ_CREDS_JSON="${AZ_CREDS_JSON:-$HOME/Projects/azure-credentials.json}"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1"; exit 1; }
}

need az
need gh
need tofu
need python3

echo "==> Azure login"
az account show >/dev/null 2>&1 || az login
az account set --subscription "$SUBSCRIPTION_ID"

echo "==> Ensure Terraform state resource group"
az group create \
  --name "$STATE_RG" \
  --location "$LOCATION" \
  --output none

echo "==> Ensure Terraform state storage account"
az storage account create \
  --name "$STATE_SA" \
  --resource-group "$STATE_RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --output none || true

echo "==> Ensure Terraform state container"
az storage container create \
  --name "$STATE_CONTAINER" \
  --account-name "$STATE_SA" \
  --auth-mode login \
  --output none || true

echo "==> Grant current user blob access to Terraform state"
USER_OBJECT_ID="$(az ad signed-in-user show --query id -o tsv)"
STATE_SCOPE="$(az storage account show --name "$STATE_SA" --resource-group "$STATE_RG" --query id -o tsv)"
az role assignment create \
  --assignee-object-id "$USER_OBJECT_ID" \
  --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "$STATE_SCOPE" \
  --output none || true

echo "==> Bootstrap Resource Group, Key Vault, and ACR"
cd infra/terraform/azure
tofu init -reconfigure -input=false -backend-config="use_azuread_auth=true"

export TF_VAR_resource_group_name="rg-mazistmtprod"
export TF_VAR_environment="prod"
export TF_VAR_location="southafricanorth"
export TF_VAR_storage_account_name="mazistmtprodsa01"
export TF_VAR_container_name="statements"
export TF_VAR_acr_name="mazistmtprodacr01"
export TF_VAR_key_vault_name="kv-mazistmtprod-01"
export TF_VAR_postgres_server_name="pg-mazistmtprod-01"
export TF_VAR_redis_container_app_name="ca-redis"
export TF_VAR_log_analytics_workspace_name="law-mazistmtprod"
export TF_VAR_container_app_environment_name="cae-mazistmtprod"
export TF_VAR_container_app_name="ca-stmt-api"
export TF_VAR_app_image="mazistmtprodacr01.azurecr.io/secure-statement-api:bootstrap"

: "${TF_VAR_statement_api_key:?Set TF_VAR_statement_api_key first}"
: "${TF_VAR_db_password:?Set TF_VAR_db_password first}"
: "${TF_VAR_redis_password:?Set TF_VAR_redis_password first}"

export TF_VAR_pdf_password_kdf_iterations="${TF_VAR_pdf_password_kdf_iterations:-600000}"
export TF_VAR_log_level="${TF_VAR_log_level:-INFO}"

tofu apply -input=false -lock-timeout=10m -auto-approve \
  -target=azurerm_resource_group.statements \
  -target=azurerm_key_vault.main \
  -target=azurerm_container_registry.main

echo "==> Import deployer Key Vault access policy if needed"
if ! tofu state show azurerm_key_vault_access_policy.deployer >/dev/null 2>&1; then
  SP_CLIENT_ID="$(python3 - <<'PY'
import json, os
p = os.environ["AZ_CREDS_JSON"]
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
print(d.get("clientId") or d.get("appId") or "")
PY
)"
  if [ -n "$SP_CLIENT_ID" ]; then
    SP_OBJECT_ID="$(az ad sp show --id "$SP_CLIENT_ID" --query id -o tsv 2>/dev/null || true)"
    if [ -n "$SP_OBJECT_ID" ]; then
      tofu import azurerm_key_vault_access_policy.deployer \
        "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$APP_RG/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME/objectId/$SP_OBJECT_ID" || true
    fi
  fi
fi

cd ../../..

echo "==> Trigger GitHub Actions deploy"
gh workflow run "$WORKFLOW" --repo "$REPO" --ref main
sleep 5

RUN_ID="$(gh run list --repo "$REPO" --workflow "$WORKFLOW" --limit 1 --json databaseId --jq '.[0].databaseId')"
gh run watch "$RUN_ID" --repo "$REPO" --exit-status