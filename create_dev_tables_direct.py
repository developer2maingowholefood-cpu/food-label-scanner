#!/usr/bin/env python3
"""
Create scan_comments table in dev environment using direct SQL commands.
This script can be run in the dev Azure App Service environment.
"""

import os
import sys
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load dev environment variables
load_dotenv()

# Set environment to use dev database
os.environ['DATABASE_URL'] = 'mssql+pyodbc://foodappadmin:DevPass123!Food@food-app-dev-server.database.windows.net:1433/food-app-dev-db?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no'

try:
    from app import app, db
    from models import ScanComment
    
    def create_dev_tables():
        """Create the scan_comments table in dev database."""
        try:
            with app.app_context():
                print("🔗 Connecting to dev Azure SQL Database...")
                print("📋 Creating scan_comments table...")
                
                # Create all tables (will only create missing ones)
                db.create_all()
                
                print("✅ Dev database tables created successfully!")
                
                # Test connection
                from sqlalchemy import text
                result = db.session.execute(text("SELECT COUNT(*) FROM scans")).scalar()
                print(f"📊 Found {result} existing scans in dev database")
                
                # Check if scan_comments table was created
                try:
                    result = db.session.execute(text("SELECT COUNT(*) FROM scan_comments")).scalar()
                    print(f"📝 scan_comments table created with {result} entries")
                except Exception as e:
                    print(f"❌ Error checking scan_comments table: {e}")
                
                print("\n✅ Dev database migration completed!")
                
        except Exception as e:
            print(f"❌ Error creating dev tables: {e}")
            return False
        
        return True
    
    if __name__ == "__main__":
        print("🚀 Creating tables in dev database...")
        
        if create_dev_tables():
            print("\n🎉 Success! Comments should now work in dev environment.")
            print("🔄 Try adding comments in the dev app: https://food-app-dev.azurewebsites.net/")
        else:
            print("\n💥 Migration failed!")
            
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 This script should be run in the dev Azure environment with all dependencies installed.")
    print("🔄 The table will be created automatically when the dev app starts and someone views scan details.")