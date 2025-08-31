# Azure SQL Database Setup Guide

## 🎯 Overview

This guide will help you set up Azure SQL Database for the food label scanner app and resolve common connection issues.

## 📋 Prerequisites

1. **Azure Subscription**: Active Azure subscription
2. **Azure SQL Database**: Already created at `foodapp-db.database.windows.net`
3. **Docker**: Local Docker environment for testing
4. **Azure CLI**: For managing Azure resources

## 🔧 Step 1: Azure SQL Database Configuration

### **Current Database Details:**

- **Server**: `foodapp-db.database.windows.net`
- **Database**: `foodlabeldb`
- **Username**: `foodappsqladmin`
- **Port**: `1433`

### **Connection String:**

```
mssql+pyodbc://foodappsqladmin:Fd100200300%21@foodapp-db.database.windows.net:1433/foodlabeldb?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

## 🔥 Step 2: Firewall Configuration

### **Issue**: Login timeout indicates firewall blocking connection

### **Solution 1: Add Current IP to Firewall**

```bash
# Get your current public IP
curl ifconfig.me

# Add your IP to Azure SQL firewall (using Azure CLI)
az sql server firewall-rule create \
  --resource-group YOUR_RESOURCE_GROUP \
  --server foodapp-db \
  --name "AllowMyIP" \
  --start-ip-address YOUR_IP_ADDRESS \
  --end-ip-address YOUR_IP_ADDRESS
```

### **Solution 2: Allow Azure Services**

```bash
# Allow Azure services to access the database
az sql server firewall-rule create \
  --resource-group YOUR_RESOURCE_GROUP \
  --server foodapp-db \
  --name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### **Solution 3: Azure Portal Configuration**

1. Go to Azure Portal
2. Navigate to your SQL Database
3. Click "Set server firewall"
4. Add your IP address or allow Azure services

## 🐳 Step 3: Docker Container Setup

### **Local Testing with Azure SQL**

```bash
# Run app with Azure SQL Database
./run_azure_sql.sh

# Test connection inside container
docker exec food-app-container python3 /app/test_azure_connection.py
```

### **Migration from SQLite to Azure SQL**

```bash
# Run migration inside container
./migrate_in_container.sh
```

## 🔍 Step 4: Troubleshooting

### **Common Issues and Solutions**

#### **1. Login Timeout**

- **Cause**: Firewall blocking connection
- **Solution**: Add IP to Azure SQL firewall

#### **2. ODBC Driver Not Found**

- **Cause**: Missing ODBC driver on host
- **Solution**: Use Docker container (drivers installed)

#### **3. Connection String Issues**

- **Cause**: Malformed connection string
- **Solution**: Check URL encoding and special characters

#### **4. SSL/TLS Issues**

- **Cause**: Certificate validation problems
- **Solution**: Use `TrustServerCertificate=no`

## 📊 Step 5: Database Schema

### **Tables to Create**

#### **Users Table**

```sql
CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    reset_token VARCHAR(128) NULL,
    reset_token_expiry DATETIME2 NULL
);
```

#### **Scans Table**

```sql
CREATE TABLE scans (
    id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    scan_data NVARCHAR(MAX) NOT NULL,
    timestamp DATETIME2 DEFAULT GETUTCDATE(),
    comments NVARCHAR(MAX) NULL,
    image_url VARCHAR(500) NULL,
    blob_name VARCHAR(200) NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## 🚀 Step 6: Production Deployment

### **Environment Variables for Production**

```bash
# Azure SQL Database
DATABASE_URL=mssql+pyodbc://username:password@server:port/database?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no

# Azure Services
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-key
AZURE_STORAGE_CONNECTION_STRING=your-connection-string

# AI Services
CLAUDE_SONNET_API_KEY=your-claude-key

# Email
BREVO_API_KEY=your-brevo-key
```

### **Docker Production Deployment**

```bash
# Build production image
docker build -t food-app:production .

# Run with production environment
docker run -d -p 8000:8000 --env-file azure-production.env --name food-app-prod food-app:production
```

## 🔐 Step 7: Security Best Practices

### **Database Security**

1. **Strong Passwords**: Use complex passwords for database users
2. **Firewall Rules**: Only allow necessary IP addresses
3. **Encryption**: Always use SSL/TLS connections
4. **Access Control**: Use least privilege principle

### **Application Security**

1. **Environment Variables**: Never commit secrets to git
2. **Connection Pooling**: Use connection pooling for performance
3. **Error Handling**: Don't expose database errors to users
4. **Input Validation**: Validate all user inputs

## 📈 Step 8: Monitoring and Maintenance

### **Database Monitoring**

```bash
# Check connection status
docker exec food-app-container python3 -c "from src.app import app, db; app.app_context().push(); print('Database connected:', db.engine.pool.checkedin())"

# Monitor resource usage
docker stats food-app-container
```

### **Backup and Recovery**

1. **Azure SQL Backups**: Automatic backups enabled
2. **Point-in-time Recovery**: Available for 7-35 days
3. **Geo-replication**: Consider for disaster recovery

## 🎯 Quick Commands Reference

```bash
# Test Azure SQL connection
docker exec food-app-container python3 /app/test_azure_connection.py

# Run migration
./migrate_in_container.sh

# Start with Azure SQL
./run_azure_sql.sh

# Start with SQLite (fallback)
./run_local.sh

# Check container logs
docker logs food-app-container -f
```

## 📞 Support

If you encounter issues:

1. **Check Firewall**: Ensure your IP is whitelisted
2. **Verify Credentials**: Check username/password
3. **Test Connection**: Use the test script
4. **Check Logs**: Review container logs for errors
5. **Azure Portal**: Verify database status in Azure Portal

---

## 🎉 Success Checklist

- [ ] Azure SQL Database created and running
- [ ] Firewall rules configured
- [ ] Connection string tested and working
- [ ] Database tables created
- [ ] Data migrated from SQLite (if applicable)
- [ ] Application running with Azure SQL
- [ ] Production environment configured
- [ ] Monitoring and backup configured
