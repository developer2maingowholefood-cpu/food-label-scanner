#!/usr/bin/env python3
"""
Simple Azure SQL Database connection test
"""

import os
import pyodbc
from dotenv import load_dotenv

# Load environment variables
load_dotenv('azure-production.env')

def test_azure_connection():
    """Test Azure SQL Database connection with detailed error reporting"""
    
    # Get connection string
    database_url = os.getenv('DATABASE_URL')
    print(f"🔗 Testing connection to Azure SQL Database...")
    print(f"📋 Connection string: {database_url[:50]}...")
    
    try:
        # Parse connection string manually for testing
        # Format: mssql+pyodbc://username:password@server:port/database?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
        
        # Extract components from the URL
        if database_url.startswith('mssql+pyodbc://'):
            # Remove the prefix
            connection_part = database_url.replace('mssql+pyodbc://', '')
            
            # Split into parts
            auth_part, rest = connection_part.split('@', 1)
            username, password = auth_part.split(':', 1)
            
            # Extract server and database
            server_part, params = rest.split('/', 1)
            server, port = server_part.split(':', 1)
            database = params.split('?')[0]
            
            print(f"🔍 Parsed connection details:")
            print(f"   Server: {server}")
            print(f"   Port: {port}")
            print(f"   Database: {database}")
            print(f"   Username: {username}")
            print(f"   Password: {'*' * len(password)}")
            
            # Create connection string for pyodbc
            conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
            
            print(f"🔗 Attempting connection...")
            print(f"📋 Connection string: {conn_str[:100]}...")
            
            # Test connection
            conn = pyodbc.connect(conn_str, timeout=30)
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT @@VERSION as version")
            result = cursor.fetchone()
            print(f"✅ Connection successful!")
            print(f"📊 SQL Server version: {result[0][:100]}...")
            
            cursor.close()
            conn.close()
            return True
            
    except pyodbc.Error as e:
        print(f"❌ ODBC Error: {e}")
        print(f"🔍 Error details: {e.args}")
        return False
    except Exception as e:
        print(f"❌ General Error: {e}")
        return False

if __name__ == "__main__":
    success = test_azure_connection()
    if success:
        print("🎉 Azure SQL Database connection test passed!")
    else:
        print("❌ Azure SQL Database connection test failed!")
        print("💡 Possible issues:")
        print("   - Firewall blocking connection")
        print("   - Azure SQL Database not running")
        print("   - Incorrect connection string")
        print("   - Network connectivity issues") 