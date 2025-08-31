#!/usr/bin/env python3
"""
Simple script to check if scans are being saved to Azure SQL Database.
Run this locally to verify data is being stored.
"""

import os
import pyodbc
from datetime import datetime

def check_azure_sql():
    """Check Azure SQL Database for scan data"""
    
    # You'll need to set these environment variables or replace with your actual values
    server = os.getenv('AZURE_SQL_SERVER', 'your-server.database.windows.net')
    database = os.getenv('AZURE_SQL_DATABASE', 'your-database')
    username = os.getenv('AZURE_SQL_USERNAME', 'your-username')
    password = os.getenv('AZURE_SQL_PASSWORD', 'your-password')
    
    print(f"🔍 Checking Azure SQL Database: {server}/{database}")
    
    try:
        # Build connection string
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;"
        
        # Connect to database
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("✅ Connected to Azure SQL Database")
        
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
            print("💡 Try uploading an image through the web app to create a scan")
            return
        
        # Get the most recent scan
        cursor.execute("""
            SELECT TOP 1 
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
        
        latest_scan = cursor.fetchone()
        
        if latest_scan:
            scan_id, user_id, image_filename, created_at, ingredients_text, is_safe, safety_score = latest_scan
            print(f"\n📝 Latest scan:")
            print(f"  ID: {scan_id}")
            print(f"  User ID: {user_id}")
            print(f"  Image: {image_filename}")
            print(f"  Created: {created_at}")
            print(f"  Safe: {is_safe}")
            print(f"  Safety Score: {safety_score}")
            if ingredients_text:
                ingredients_preview = ingredients_text[:100] + "..." if len(ingredients_text) > 100 else ingredients_text
                print(f"  Ingredients: {ingredients_preview}")
        
        # Get scans from last 24 hours
        cursor.execute("""
            SELECT COUNT(*) 
            FROM scans 
            WHERE created_at >= DATEADD(day, -1, GETDATE())
        """)
        
        recent_scans = cursor.fetchone()[0]
        print(f"\n📈 Scans in last 24 hours: {recent_scans}")
        
        conn.close()
        print("✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("  1. ODBC Driver 18 for SQL Server installed")
        print("  2. Correct Azure SQL credentials")
        print("  3. Your IP added to Azure SQL firewall")

if __name__ == "__main__":
    check_azure_sql() 