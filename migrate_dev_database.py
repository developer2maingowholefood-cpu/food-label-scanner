#!/usr/bin/env python3
"""
Create scan_comments table specifically for dev Azure SQL Database.
"""

import os
import pyodbc
from urllib.parse import quote_plus

def migrate_dev_database():
    """Create the scan_comments table in dev Azure SQL Database."""
    
    # Dev database connection details
    server = 'food-app-dev-server.database.windows.net'
    database = 'food-app-dev-db'
    username = 'foodappadmin'
    password = 'DevPass123!Food'
    
    # Connection string for Azure SQL Database
    connection_string = f'''
    DRIVER={{ODBC Driver 18 for SQL Server}};
    SERVER={server};
    DATABASE={database};
    UID={username};
    PWD={password};
    Encrypt=yes;
    TrustServerCertificate=no;
    Connection Timeout=30;
    '''
    
    print("🔗 Connecting to dev Azure SQL Database...")
    print(f"Server: {server}")
    print(f"Database: {database}")
    
    try:
        # Connect to database
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # Check if scan_comments table already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'scan_comments'
        """)
        
        table_exists = cursor.fetchone()[0] > 0
        
        if table_exists:
            print("✅ scan_comments table already exists!")
        else:
            print("📋 Creating scan_comments table...")
            
            # Create scan_comments table
            create_table_sql = """
            CREATE TABLE scan_comments (
                id int IDENTITY(1,1) PRIMARY KEY,
                scan_id int NOT NULL,
                comment_text nvarchar(max) NOT NULL,
                timestamp datetime2 DEFAULT GETUTCDATE(),
                created_at datetime2 DEFAULT GETUTCDATE(),
                FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
            );
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            print("✅ scan_comments table created successfully!")
        
        # Show table structure
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'scan_comments'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print("\n📋 Table Structure:")
        for column in columns:
            nullable = "NULL" if column[2] == "YES" else "NOT NULL"
            print(f"  - {column[0]}: {column[1]} ({nullable})")
        
        # Check if there are any existing comments to migrate
        cursor.execute("SELECT COUNT(*) FROM scans WHERE comments IS NOT NULL AND comments != ''")
        legacy_comments_count = cursor.fetchone()[0]
        
        if legacy_comments_count > 0:
            print(f"\n📝 Found {legacy_comments_count} scans with legacy comments")
            print("💡 These will be automatically migrated when users view scan details")
        else:
            print("\n📝 No legacy comments found")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Dev database migration completed successfully!")
        print("🔄 New comments will now be saved to the scan_comments table")
        
        return True
        
    except Exception as e:
        print(f"❌ Error migrating dev database: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Migrating dev Azure SQL Database...")
    
    if migrate_dev_database():
        print("\n🎉 Migration successful! Comments should now work in dev environment.")
    else:
        print("\n💥 Migration failed! Check the error above.")