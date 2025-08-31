#!/bin/bash

# Azure Container Registry name (replace with your actual registry name)
ACR_NAME="foodappregistry"

# Resource group name
RESOURCE_GROUP="food-app-rg"

# Container Instance name
CONTAINER_NAME="food-app-container"

# Image name and tag
IMAGE_NAME="food-app"
IMAGE_TAG="latest"

echo "Building Docker image..."
docker build -t $IMAGE_NAME:$IMAGE_TAG .

echo "Logging into Azure Container Registry..."
az acr login --name $ACR_NAME

echo "Tagging image for Azure Container Registry..."
docker tag $IMAGE_NAME:$IMAGE_TAG $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

echo "Pushing image to Azure Container Registry..."
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

echo "Deploying to Azure Container Instances..."
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_NAME \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG \
  --dns-name-label food-app-container \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="mssql+pyodbc://foodappsqladmin:Fd100200300%21@foodapp-db.database.windows.net:1433/foodlabeldb?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no" \
    AZURE_FORM_RECOGNIZER_ENDPOINT="https://food-app-form-recognizer.cognitiveservices.azure.com/" \
    AZURE_FORM_RECOGNIZER_KEY="your-form-recognizer-key" \
    AZURE_STORAGE_CONNECTION_STRING="your-blob-storage-connection-string" \
    CLAUDE_API_KEY="your-claude-api-key" \
    BREVO_API_KEY="your-brevo-api-key" \
    SECRET_KEY="your-secret-key"

echo "Deployment complete! Your app should be available at:"
echo "http://food-app-container.eastus2.azurecontainer.io" 