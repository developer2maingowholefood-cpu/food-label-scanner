#!/bin/bash

# Azure Dev Environment Configuration with Consistent Naming
# Configures environment variables for food-app-dev.azurewebsites.net

set -e

# Variables with consistent naming
RESOURCE_GROUP="food-app-dev-rg"
APP_NAME="food-app-dev"
SQL_SERVER="food-app-dev-server"
DATABASE_NAME="food-app-dev-db"
STORAGE_ACCOUNT="foodappdevstorage"
CONTAINER_NAME="food-app-dev-images"

# Database connection string
DATABASE_URL="mssql+pyodbc://foodappadmin:DevPass123!Food@$SQL_SERVER.database.windows.net:1433/$DATABASE_NAME?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"

# Get storage account key
echo "🔑 Getting storage account key..."
STORAGE_KEY=$(az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT --query '[0].value' --output tsv)

# Production values (shared with dev for cost efficiency)
FORM_RECOGNIZER_ENDPOINT="https://foodappdocintel.cognitiveservices.azure.com/"
FORM_RECOGNIZER_KEY="YOUR_AZURE_FORM_RECOGNIZER_KEY"
CLAUDE_API_KEY="YOUR_CLAUDE_API_KEY"
BREVO_API_KEY="YOUR_BREVO_API_KEY"
EMAIL_SENDER="developer.main.gowholefood@gmail.com"

# Generate a new secret key for dev (different from prod)
SECRET_KEY="dev-secret-key-$(date +%s)-food-app"

echo "🔧 Configuring Azure Web App environment variables..."
echo "📱 App Name: $APP_NAME"
echo "🌐 URL: https://$APP_NAME.azurewebsites.net"

az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
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
echo "✅ Dev environment configuration complete!"
echo "🌐 Dev URL: https://$APP_NAME.azurewebsites.net"
echo ""
echo "📋 Consistent Naming Pattern:"
echo "  Production: food-app.azurewebsites.net"
echo "  Dev:        food-app-dev.azurewebsites.net"
echo "  Future UAT: food-app-uat.azurewebsites.net"
echo ""
echo "🔧 Next steps:"
echo "1. Update GitHub workflow to use new naming"
echo "2. Get publish profile for GitHub Actions"
echo "3. Test deployment"