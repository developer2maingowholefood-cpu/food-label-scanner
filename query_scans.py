#!/usr/bin/env python3
"""
Script to query Azure SQL Database and check if scans are being saved.
"""

import os
import pyodbc
from datetime import datetime
import json

def get_connection():
    """Get connection to Azure SQL Database"""
    # Get connection string from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return None
    
    try:
        # Parse connection string
        # Format: mssql+pyodbc://username:password@server.database.windows.net:1433/database?driver=ODBC+Driver+18+for+SQL+Server
        if database_url.startswith('mssql+pyodbc://'):
            # Remove the mssql+pyodbc:// prefix
            connection_string = database_url.replace('mssql+pyodbc://', '')
            
            # Extract components
            auth_part, rest = connection_string.split('@', 1)
            username, password = auth_part.split(':', 1)
            
            server_part, database_part = rest.split('/', 1)
            server = server_part.split(':')[0]  # Remove port if present
            database = database_part.split('?')[0]  # Remove query parameters
            
            # Build ODBC connection string
            conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;"
        else:
            print("❌ Unexpected DATABASE_URL format")
            return None
            
        conn = pyodbc.connect(conn_str)
        print("✅ Connected to Azure SQL Database")
        return conn
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def check_tables(conn):
    """Check what tables exist in the database"""
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    
    tables = cursor.fetchall()
    print(f"\n📋 Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    return [table[0] for table in tables]

def query_scans(conn):
    """Query scan data"""
    cursor = conn.cursor()
    
    print(f"\n🔍 Querying scan data...")
    
    # Check if scans table exists
    cursor.execute("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'scans'
    """)
    
    if cursor.fetchone()[0] == 0:
        print("❌ 'scans' table does not exist")
        return
    
    # Get total count of scans
    cursor.execute("SELECT COUNT(*) FROM scans")
    total_scans = cursor.fetchone()[0]
    print(f"📊 Total scans in database: {total_scans}")
    
    if total_scans == 0:
        print("⚠️  No scans found in database")
        return
    
    # Get recent scans
    cursor.execute("""
        SELECT TOP 10 
            id, 
            user_id, 
            image_filename, 
            created_at,
            ingredients_text,
            is_safe,
            safety_score
        FROM scans 
        ORDER BY created_at DESC
    """)
    
    recent_scans = cursor.fetchall()
    
    print(f"\n📝 Recent scans (last 10):")
    print("-" * 80)
    for scan in recent_scans:
        scan_id, user_id, image_filename, created_at, ingredients_text, is_safe, safety_score = scan
        print(f"ID: {scan_id}")
        print(f"User ID: {user_id}")
        print(f"Image: {image_filename}")
        print(f"Created: {created_at}")
        print(f"Safe: {is_safe}")
        print(f"Safety Score: {safety_score}")
        if ingredients_text:
            ingredients_preview = ingredients_text[:100] + "..." if len(ingredients_text) > 100 else ingredients_text
            print(f"Ingredients: {ingredients_preview}")
        print("-" * 80)

def query_users(conn):
    """Query user data"""
    cursor = conn.cursor()
    
    print(f"\n👥 Querying user data...")
    
    # Check if users table exists
    cursor.execute("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'users'
    """)
    
    if cursor.fetchone()[0] == 0:
        print("❌ 'users' table does not exist")
        return
    
    # Get total count of users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    print(f"📊 Total users in database: {total_users}")
    
    if total_users == 0:
        print("⚠️  No users found in database")
        return
    
    # Get recent users
    cursor.execute("""
        SELECT TOP 5 
            id, 
            username, 
            email, 
            created_at
        FROM users 
        ORDER BY created_at DESC
    """)
    
    recent_users = cursor.fetchall()
    
    print(f"\n👤 Recent users (last 5):")
    print("-" * 60)
    for user in recent_users:
        user_id, username, email, created_at = user
        print(f"ID: {user_id}")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Created: {created_at}")
        print("-" * 60)

def get_database_stats(conn):
    """Get overall database statistics"""
    cursor = conn.cursor()
    
    print(f"\n📈 Database Statistics:")
    
    # Get table sizes
    cursor.execute("""
        SELECT 
            t.NAME AS TableName,
            p.rows AS RowCounts,
            SUM(a.total_pages) * 8 AS TotalSpaceKB
        FROM sys.tables t
        INNER JOIN sys.indexes i ON t.OBJECT_ID = i.object_id
        INNER JOIN sys.partitions p ON i.object_id = p.OBJECT_ID AND i.index_id = p.index_id
        INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
        WHERE t.NAME NOT LIKE 'dt%' 
        AND t.is_ms_shipped = 0
        AND i.OBJECT_ID > 255 
        GROUP BY t.NAME, p.Rows
        ORDER BY t.NAME
    """)
    
    tables = cursor.fetchall()
    
    for table in tables:
        table_name, row_count, space_kb = table
        print(f"  {table_name}: {row_count} rows, {space_kb} KB")

def main():
    """Main function"""
    print("🔍 Azure SQL Database Query Tool")
    print("=" * 50)
    
    # Connect to database
    conn = get_connection()
    if not conn:
        return
    
    try:
        # Check what tables exist
        tables = check_tables(conn)
        
        # Query scans
        query_scans(conn)
        
        # Query users
        query_users(conn)
        
        # Get database stats
        get_database_stats(conn)
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
    finally:
        conn.close()
        print(f"\n✅ Database connection closed")

if __name__ == "__main__":
    main() 