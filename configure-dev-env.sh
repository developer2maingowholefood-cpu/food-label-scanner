#!/bin/bash

# Azure Dev Environment Configuration
# Fill in the values below and run this script

# Database connection (already configured)
DATABASE_URL="mssql+pyodbc://foodscanneradmin:DevPass123!Food@food-scanner-dev-server.database.windows.net:1433/food-scanner-dev-db?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"

# Storage (already configured)
STORAGE_KEY=$(az storage account keys list --resource-group food-scanner-dev-rg --account-name foodscannerdevstorage --query '[0].value' --output tsv)

# Production values (shared with dev for cost efficiency)
FORM_RECOGNIZER_ENDPOINT="https://foodappdocintel.cognitiveservices.azure.com/"
FORM_RECOGNIZER_KEY="YOUR_AZURE_FORM_RECOGNIZER_KEY"
CLAUDE_API_KEY="YOUR_CLAUDE_API_KEY"
BREVO_API_KEY="YOUR_BREVO_API_KEY"
EMAIL_SENDER="developer.main.gowholefood@gmail.com"

# Generate a new secret key for dev (different from prod)
SECRET_KEY="dev-secret-key-$(date +%s)-food-scanner"

echo "🔧 Configuring Azure Web App environment variables..."

az webapp config appsettings set \
  --resource-group food-scanner-dev-rg \
  --name food-scanner-dev \
  --settings \
    DATABASE_URL="$DATABASE_URL" \
    AZURE_FORM_RECOGNIZER_ENDPOINT="$FORM_RECOGNIZER_ENDPOINT" \
    AZURE_FORM_RECOGNIZER_KEY="$FORM_RECOGNIZER_KEY" \
    AZURE_STORAGE_ACCOUNT_NAME="foodscannerdevstorage" \
    AZURE_STORAGE_ACCOUNT_KEY="$STORAGE_KEY" \
    AZURE_STORAGE_CONTAINER_NAME="food-scanner-dev-images" \
    CLAUDE_SONNET_API_KEY="$CLAUDE_API_KEY" \
    BREVO_API_KEY="$BREVO_API_KEY" \
    MAIL_DEFAULT_SENDER="$EMAIL_SENDER" \
    SECRET_KEY="$SECRET_KEY" \
  --output table

echo ""
echo "✅ Dev environment configuration complete!"
echo "🌐 Dev URL: https://food-scanner-dev.azurewebsites.net"
echo ""
echo "Next steps:"
echo "1. Get publish profile for GitHub Actions"
echo "2. Create dev branch and deploy"