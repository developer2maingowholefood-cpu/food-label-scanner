#!/usr/bin/env python3
"""
Migration script to move from SQLite to Azure SQL Database
This script will:
1. Test Azure SQL connection
2. Create tables in Azure SQL
3. Migrate data from SQLite to Azure SQL
4. Verify the migration
"""

import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('azure-production.env')

def test_azure_connection():
    """Test Azure SQL Database connection"""
    try:
        import pyodbc
        from sqlalchemy import create_engine, text
        
        # Get Azure SQL connection string
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
            
        print("🔗 Testing Azure SQL Database connection...")
        
        # Test connection
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            print("✅ Azure SQL Database connection successful!")
            return True
            
    except Exception as e:
        print(f"❌ Azure SQL Database connection failed: {e}")
        return False

def create_azure_tables():
    """Create tables in Azure SQL Database"""
    try:
        from src.app import app, db
        
        print("🏗️ Creating tables in Azure SQL Database...")
        
        with app.app_context():
            db.create_all()
            print("✅ Tables created successfully in Azure SQL Database!")
            return True
            
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def migrate_data_from_sqlite():
    """Migrate data from SQLite to Azure SQL Database"""
    try:
        from src.app import app, db
        from src.models import User, Scan
        
        sqlite_path = './instance/local.db'
        
        if not os.path.exists(sqlite_path):
            print("❌ SQLite database not found at ./instance/local.db")
            return False
            
        print("📦 Migrating data from SQLite to Azure SQL Database...")
        
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Get users from SQLite
        sqlite_cursor.execute("SELECT id, email, password_hash, created_at FROM users")
        users_data = sqlite_cursor.fetchall()
        
        # Get scans from SQLite
        sqlite_cursor.execute("SELECT id, user_id, scan_data, timestamp, comments, image_url, blob_name FROM scans")
        scans_data = sqlite_cursor.fetchall()
        
        print(f"📊 Found {len(users_data)} users and {len(scans_data)} scans to migrate")
        
        # Migrate to Azure SQL
        with app.app_context():
            # Migrate users
            for user_data in users_data:
                user_id, email, password_hash, created_at = user_data
                
                # Check if user already exists
                existing_user = User.query.filter_by(email=email).first()
                if not existing_user:
                    user = User(
                        id=user_id,
                        email=email,
                        password_hash=password_hash,
                        created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow()
                    )
                    db.session.add(user)
                    print(f"👤 Migrated user: {email}")
                else:
                    print(f"👤 User already exists: {email}")
            
            # Migrate scans
            for scan_data in scans_data:
                scan_id, user_id, scan_data_json, timestamp, comments, image_url, blob_name = scan_data
                
                # Check if scan already exists
                existing_scan = Scan.query.filter_by(id=scan_id).first()
                if not existing_scan:
                    scan = Scan(
                        id=scan_id,
                        user_id=user_id,
                        scan_data=scan_data_json,
                        timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow(),
                        comments=comments,
                        image_url=image_url,
                        blob_name=blob_name
                    )
                    db.session.add(scan)
                    print(f"📸 Migrated scan: {scan_id}")
                else:
                    print(f"📸 Scan already exists: {scan_id}")
            
            # Commit all changes
            db.session.commit()
            print("✅ Data migration completed successfully!")
            
        sqlite_conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Data migration failed: {e}")
        return False

def verify_migration():
    """Verify the migration by checking data in Azure SQL"""
    try:
        from src.app import app, db
        from src.models import User, Scan
        
        print("🔍 Verifying migration...")
        
        with app.app_context():
            # Count users and scans
            user_count = User.query.count()
            scan_count = Scan.query.count()
            
            print(f"✅ Verification complete:")
            print(f"   👥 Users in Azure SQL: {user_count}")
            print(f"   📸 Scans in Azure SQL: {scan_count}")
            
            # Show some sample data
            if user_count > 0:
                sample_user = User.query.first()
                print(f"   📧 Sample user: {sample_user.email}")
                
            if scan_count > 0:
                sample_scan = Scan.query.first()
                print(f"   📅 Sample scan: {sample_scan.timestamp}")
                
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting SQLite to Azure SQL Database Migration")
    print("=" * 60)
    
    # Step 1: Test Azure SQL connection
    if not test_azure_connection():
        print("❌ Migration aborted - Azure SQL connection failed")
        return False
    
    # Step 2: Create tables in Azure SQL
    if not create_azure_tables():
        print("❌ Migration aborted - Failed to create tables")
        return False
    
    # Step 3: Migrate data
    if not migrate_data_from_sqlite():
        print("❌ Migration aborted - Failed to migrate data")
        return False
    
    # Step 4: Verify migration
    if not verify_migration():
        print("❌ Migration verification failed")
        return False
    
    print("=" * 60)
    print("🎉 Migration completed successfully!")
    print("✅ Your app is now using Azure SQL Database")
    print("🌐 You can now deploy to Azure with confidence!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 