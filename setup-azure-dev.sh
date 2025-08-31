#!/bin/bash

# Azure Dev Environment Setup Script
# Food Label Scanner Development Environment

set -e  # Exit on any error

echo "🚀 Setting up Azure Development Environment for Food Label Scanner..."

# Configuration
RESOURCE_GROUP="food-scanner-dev-rg"
APP_SERVICE_PLAN="food-scanner-dev-plan"
WEB_APP_NAME="food-scanner-dev"
SQL_SERVER="food-scanner-dev-server"
DATABASE_NAME="food-scanner-dev-db"
STORAGE_ACCOUNT="foodscannerdevstorage"
CONTAINER_NAME="food-scanner-dev-images"
LOCATION="East US"

# Check if logged in to Azure
echo "📝 Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure login confirmed"

# Create Resource Group
echo "📦 Creating resource group: $RESOURCE_GROUP"
az group create \
  --name $RESOURCE_GROUP \
  --location "$LOCATION" \
  --output table

# Create App Service Plan (B1 for cost optimization)
echo "🏗️  Creating App Service Plan: $APP_SERVICE_PLAN (B1 tier for dev)"
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux \
  --output table

# Create Web App
echo "🌐 Creating Web App: $WEB_APP_NAME"
az webapp create \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --runtime "PYTHON:3.11" \
  --output table

# Create SQL Server
echo "🗄️  Creating SQL Server: $SQL_SERVER"
echo "⚠️  Please enter a secure password for the SQL admin user:"
read -s SQL_PASSWORD

az sql server create \
  --name $SQL_SERVER \
  --resource-group $RESOURCE_GROUP \
  --location "$LOCATION" \
  --admin-user foodscanneradmin \
  --admin-password "$SQL_PASSWORD" \
  --output table

# Create Database
echo "📊 Creating Database: $DATABASE_NAME"
az sql db create \
  --resource-group $RESOURCE_GROUP \
  --server $SQL_SERVER \
  --name $DATABASE_NAME \
  --service-objective S0 \
  --output table

# Create Storage Account
echo "💾 Creating Storage Account: $STORAGE_ACCOUNT"
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location "$LOCATION" \
  --sku "Standard_LRS" \
  --output table

# Create Storage Container
echo "📁 Creating Storage Container: $CONTAINER_NAME"
az storage container create \
  --name $CONTAINER_NAME \
  --account-name $STORAGE_ACCOUNT \
  --public-access off \
  --output table

# Get Storage Account Key
echo "🔑 Retrieving storage account key..."
STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query '[0].value' \
  --output tsv)

# Create Database URL
DATABASE_URL="mssql+pyodbc://foodscanneradmin:${SQL_PASSWORD}@${SQL_SERVER}.database.windows.net:1433/${DATABASE_NAME}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"

echo "🔧 Configuring environment variables..."
echo "⚠️  You'll need to provide the following values:"
echo "   - Azure Form Recognizer Endpoint & Key (can share with prod)"
echo "   - Claude Sonnet API Key (shared with prod - OK for dev)"
echo "   - Brevo API Key (can share with prod)"
echo "   - Default Email Sender"

read -p "Azure Form Recognizer Endpoint: " FORM_RECOGNIZER_ENDPOINT
read -p "Azure Form Recognizer Key: " FORM_RECOGNIZER_KEY
read -p "Claude Sonnet API Key (shared with prod): " CLAUDE_API_KEY
read -p "Brevo API Key (can share with prod): " BREVO_API_KEY
read -p "Default Email Sender: " EMAIL_SENDER
read -p "Secret Key for DEV (different from prod): " SECRET_KEY

# Set App Settings
echo "⚙️  Setting application configuration..."
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $WEB_APP_NAME \
  --settings \
    DATABASE_URL="$DATABASE_URL" \
    AZURE_FORM_RECOGNIZER_ENDPOINT="$FORM_RECOGNIZER_ENDPOINT" \
    AZURE_FORM_RECOGNIZER_KEY="$FORM_RECOGNIZER_KEY" \
    AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT" \
    AZURE_STORAGE_ACCOUNT_KEY="$STORAGE_KEY" \
    AZURE_STORAGE_CONTAINER_NAME="$CONTAINER_NAME" \
    CLAUDE_SONNET_API_KEY="$CLAUDE_API_KEY" \
    BREVO_API_KEY="$BREVO_API_KEY" \
    MAIL_DEFAULT_SENDER="$EMAIL_SENDER" \
    SECRET_KEY="$SECRET_KEY" \
  --output table

echo ""
echo "🎉 Azure Dev Environment Setup Complete!"
echo ""
echo "📋 Summary:"
echo "   🌐 Web App URL: https://${WEB_APP_NAME}.azurewebsites.net"
echo "   📦 Resource Group: $RESOURCE_GROUP"
echo "   🏗️  App Service: $WEB_APP_NAME (B1 tier - cost optimized)"
echo "   🗄️  SQL Server: ${SQL_SERVER}.database.windows.net"
echo "   📊 Database: $DATABASE_NAME (separate from prod)"
echo "   💾 Storage: $STORAGE_ACCOUNT (separate dev images)"
echo "   🔑 Shared APIs: Form Recognizer, Claude Sonnet, Brevo (cost efficient)"
echo ""
echo "💰 Estimated Monthly Cost:"
echo "   • App Service B1: ~$13/month"
echo "   • SQL Database S0: ~$15/month"
echo "   • Storage Account: ~$2-5/month"
echo "   • Total: ~$30-33/month (vs $50+ with B2)"
echo ""
echo "🔄 Next Steps:"
echo "   1. Get publish profile: az webapp deployment list-publishing-profiles --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --xml"
echo "   2. Add publish profile to GitHub Secrets as AZURE_WEBAPP_PUBLISH_PROFILE_DEV"
echo "   3. Create 'dev' branch: git checkout -b dev && git push -u origin dev"
echo "   4. Configure SQL firewall if needed: az sql server firewall-rule create"
echo "   5. Test deployment with the GitHub Actions workflow"
echo ""