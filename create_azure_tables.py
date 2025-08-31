#!/usr/bin/env python3
"""
Simple script to create tables in Azure SQL Database
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('azure-production.env')

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

if __name__ == "__main__":
    success = create_azure_tables()
    if success:
        print("🎉 Azure SQL Database tables created successfully!")
    else:
        print("❌ Failed to create Azure SQL Database tables!") 