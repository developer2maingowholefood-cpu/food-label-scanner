#!/bin/bash

# Azure Dev Environment Setup with Consistent Naming
# Production: food-app.azurewebsites.net
# Dev: food-app-dev.azurewebsites.net
# Future UAT: food-app-uat.azurewebsites.net

set -e

echo "🚀 Setting up Azure Dev Environment with Consistent Naming..."
echo "📋 Target: food-app-dev.azurewebsites.net"

# Variables with consistent naming
RESOURCE_GROUP="food-app-dev-rg"
LOCATION="West US"
APP_NAME="food-app-dev"
APP_SERVICE_PLAN="food-app-dev-plan"
SQL_SERVER="food-app-dev-server"
DATABASE_NAME="food-app-dev-db"
STORAGE_ACCOUNT="foodappdevstorage"  # Storage accounts can't have hyphens
CONTAINER_NAME="food-app-dev-images"

echo "📦 Creating Resource Group: $RESOURCE_GROUP"
az group create \
  --name $RESOURCE_GROUP \
  --location "$LOCATION"

echo "💾 Creating SQL Server: $SQL_SERVER"
az sql server create \
  --resource-group $RESOURCE_GROUP \
  --name $SQL_SERVER \
  --location "$LOCATION" \
  --admin-user foodappadmin \
  --admin-password "DevPass123!Food"

echo "📊 Creating SQL Database: $DATABASE_NAME"
az sql db create \
  --resource-group $RESOURCE_GROUP \
  --server $SQL_SERVER \
  --name $DATABASE_NAME \
  --edition Basic \
  --capacity 5

echo "🔧 Configuring SQL Server firewall"
az sql server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --server $SQL_SERVER \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

echo "💾 Creating Storage Account: $STORAGE_ACCOUNT"
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

echo "📦 Creating Storage Container: $CONTAINER_NAME"
az storage container create \
  --account-name $STORAGE_ACCOUNT \
  --name $CONTAINER_NAME \
  --public-access off

echo "🌐 Creating App Service Plan: $APP_SERVICE_PLAN"
az appservice plan create \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_PLAN \
  --location "$LOCATION" \
  --sku F1 \
  --is-linux

echo "🚀 Creating Web App: $APP_NAME"
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $APP_NAME \
  --runtime "PYTHON:3.11"

echo "✅ Dev environment created successfully!"
echo ""
echo "📋 Resource Summary:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Web App: $APP_NAME"
echo "  URL: https://$APP_NAME.azurewebsites.net"
echo "  SQL Server: $SQL_SERVER"
echo "  Database: $DATABASE_NAME"
echo "  Storage: $STORAGE_ACCOUNT"
echo ""
echo "🔧 Next steps:"
echo "1. Run configure-dev-env-consistent.sh to set environment variables"
echo "2. Update GitHub secrets for dev deployment"
echo "3. Test deployment to dev environment"