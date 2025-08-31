#!/bin/bash

echo "🔧 Azure SQL Database Firewall Configuration Helper"
echo "=================================================="

# Get current public IP
echo "🌐 Getting your current public IP address..."
CURRENT_IP=$(curl -s ifconfig.me)

echo ""
echo "📋 Your current public IP address is: $CURRENT_IP"
echo ""

echo "🔧 To allow this IP in Azure SQL Database firewall:"
echo ""
echo "Option 1: Azure CLI (recommended)"
echo "----------------------------------"
echo "az sql server firewall-rule create \\"
echo "  --resource-group YOUR_RESOURCE_GROUP \\"
echo "  --server foodapp-db \\"
echo "  --name \"AllowMyIP\" \\"
echo "  --start-ip-address $CURRENT_IP \\"
echo "  --end-ip-address $CURRENT_IP"
echo ""

echo "Option 2: Azure Portal"
echo "----------------------"
echo "1. Go to Azure Portal"
echo "2. Navigate to your SQL Database"
echo "3. Click 'Set server firewall'"
echo "4. Add rule:"
echo "   - Name: AllowMyIP"
echo "   - Start IP: $CURRENT_IP"
echo "   - End IP: $CURRENT_IP"
echo ""

echo "Option 3: Allow Azure Services (for production)"
echo "-----------------------------------------------"
echo "az sql server firewall-rule create \\"
echo "  --resource-group YOUR_RESOURCE_GROUP \\"
echo "  --server foodapp-db \\"
echo "  --name \"AllowAzureServices\" \\"
echo "  --start-ip-address 0.0.0.0 \\"
echo "  --end-ip-address 0.0.0.0"
echo ""

echo "🔍 After configuring firewall, test connection:"
echo "docker exec food-app-container python3 /app/test_azure_connection.py"
echo ""

echo "📊 Current Azure SQL Database Details:"
echo "   Server: foodapp-db.database.windows.net"
echo "   Database: foodlabeldb"
echo "   Username: foodappsqladmin"
echo "   Port: 1433"
echo ""

echo "💡 Tips:"
echo "- Your IP might change if you're on a dynamic connection"
echo "- For production, consider using Azure App Service with managed identity"
echo "- Always use SSL/TLS connections (Encrypt=yes)"
echo "- Test connection before running migration" 