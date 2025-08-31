# Azure Blob Storage Setup Guide

This guide explains how to set up Azure Blob Storage for image storage in the Food Label Scanner app.

## Local Testing (No Azure Required)

For local testing, you don't need Azure Blob Storage credentials. The app will automatically save images to a local directory:

1. **No configuration needed** - Just run the app locally
2. Images will be saved to `local_storage/images/` directory
3. Images will be served via `/local_storage/images/` route

## Production Setup (Azure Blob Storage)

### 1. Create Azure Storage Account

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new Storage Account
3. Note down:
   - Storage Account Name
   - Access Key (or generate a new one)

### 2. Create Blob Container

1. In your Storage Account, go to "Containers"
2. Create a new container named `food-scanner-images`
3. Set access level to "Private" (recommended) or "Blob" (public read)

### 3. Environment Variables

Set these environment variables in your Heroku app or local `.env` file:

#### Option 1: Connection String (Recommended)

```
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=YOUR_ACCOUNT;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net
```

#### Option 2: Account Name and Key

```
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account-name
AZURE_STORAGE_ACCOUNT_KEY=your-storage-account-key
```

#### Optional Configuration

```
AZURE_STORAGE_CONTAINER_NAME=food-scanner-images  # Default value
```

### 4. Heroku Deployment

Add the environment variables to your Heroku app:

```bash
heroku config:set AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
heroku config:set AZURE_STORAGE_ACCOUNT_NAME="your-account-name"
heroku config:set AZURE_STORAGE_ACCOUNT_KEY="your-account-key"
```

### 5. Database Migration

Run the database migration to add image storage fields:

```bash
# If using Flask-Migrate
flask db upgrade

# Or manually run the migration
python -c "from src.app import app, db; app.app_context().push(); db.create_all()"
```

## Features

### Local Testing

- ✅ Images saved to local directory
- ✅ Images served via Flask route
- ✅ No Azure credentials required
- ✅ Perfect for development

### Production (Azure)

- ✅ Images uploaded to Azure Blob Storage
- ✅ Secure access with SAS tokens
- ✅ Scalable cloud storage
- ✅ Automatic container creation

### Both Environments

- ✅ Image previews in dashboard
- ✅ Image display in scan details
- ✅ Automatic fallback if Azure fails
- ✅ User-specific image organization

## Testing

1. **Local Testing**: Just run the app - no Azure setup needed
2. **Production Testing**: Set up Azure credentials and test image uploads
3. **Mixed Testing**: Use local storage for development, Azure for production

## Troubleshooting

### Local Testing Issues

- Ensure `local_storage/images/` directory is writable
- Check that the `/local_storage/images/` route is working

### Azure Issues

- Verify connection string or account credentials
- Check container permissions
- Ensure container name matches environment variable
- Check Azure Storage account quotas and limits

### Database Issues

- Run database migrations: `flask db upgrade`
- Check that `image_url` and `blob_name` columns exist in scans table
