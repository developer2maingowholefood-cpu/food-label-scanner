#!/usr/bin/env python3
"""
Debug script to check Azure SQL Database structure and data.
"""

import os
import pyodbc
from datetime import datetime

def debug_azure_sql():
    """Debug Azure SQL Database"""
    
    # Set environment variables for Azure SQL
    server = 'foodappsqladmin.database.windows.net'
    database = 'foogapp-db'
    username = 'foodappsqladmin'
    password = 'FdAp100200300!'
    
    print(f"🔍 Debugging Azure SQL Database: {server}/{database}")
    
    try:
        # Build connection string
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;"
        
        # Connect to database
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("✅ Connected to Azure SQL Database")
        
        # Check all tables
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
        
        # Check if scans table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'scans'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("\n❌ 'scans' table does not exist in Azure SQL")
            print("💡 The app might be creating tables in SQLite instead")
            return
        
        # Get scans table structure
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'scans'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print(f"\n📊 Scans table structure:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
        
        # Get total count of scans
        cursor.execute("SELECT COUNT(*) FROM scans")
        total_scans = cursor.fetchone()[0]
        print(f"\n📊 Total scans in Azure SQL: {total_scans}")
        
        if total_scans > 0:
            # Get recent scans
            cursor.execute("""
                SELECT TOP 5 
                    id, 
                    user_id, 
                    timestamp,
                    image_url,
                    blob_name
                FROM scans 
                ORDER BY timestamp DESC
            """)
            
            recent_scans = cursor.fetchall()
            
            print(f"\n📝 Recent scans in Azure SQL:")
            for scan in recent_scans:
                scan_id, user_id, timestamp, image_url, blob_name = scan
                print(f"  ID: {scan_id}, User: {user_id}, Time: {timestamp}")
                print(f"    Image: {image_url}")
                print(f"    Blob: {blob_name}")
                print()
        
        # Check users table
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'users'
        """)
        
        if cursor.fetchone()[0] > 0:
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            print(f"👥 Total users in Azure SQL: {total_users}")
        
        conn.close()
        print("✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_azure_sql() 