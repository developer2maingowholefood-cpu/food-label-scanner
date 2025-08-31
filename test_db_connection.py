#!/usr/bin/env python3
"""
Test script to check database connection and save operations.
"""

import os
import sys
sys.path.append('src')

from app import app, db
from models import User, Scan
import json

def test_db_connection():
    """Test database connection and save operations"""
    
    with app.app_context():
        try:
            print("🔍 Testing database connection...")
            
            # Test 1: Check if we can connect
            db.engine.execute("SELECT 1")
            print("✅ Database connection successful")
            
            # Test 2: Check if tables exist
            result = db.engine.execute("SELECT COUNT(*) FROM users")
            user_count = result.fetchone()[0]
            print(f"📊 Users in database: {user_count}")
            
            result = db.engine.execute("SELECT COUNT(*) FROM scans")
            scan_count = result.fetchone()[0]
            print(f"📊 Scans in database: {scan_count}")
            
            # Test 3: Try to create a test user
            print("\n🧪 Testing user creation...")
            test_user = User(email="test@example.com")
            test_user.set_password("testpassword")
            db.session.add(test_user)
            db.session.commit()
            print("✅ Test user created successfully")
            
            # Test 4: Try to create a test scan
            print("\n🧪 Testing scan creation...")
            test_scan = Scan(
                user_id=test_user.id,
                scan_data={"test": "data"},
                image_url="test_url",
                blob_name="test_blob"
            )
            db.session.add(test_scan)
            db.session.commit()
            print("✅ Test scan created successfully")
            
            # Test 5: Verify the data was saved
            result = db.engine.execute("SELECT COUNT(*) FROM users")
            new_user_count = result.fetchone()[0]
            print(f"📊 Users after test: {new_user_count}")
            
            result = db.engine.execute("SELECT COUNT(*) FROM scans")
            new_scan_count = result.fetchone()[0]
            print(f"📊 Scans after test: {new_scan_count}")
            
            # Clean up test data
            db.session.delete(test_scan)
            db.session.delete(test_user)
            db.session.commit()
            print("🧹 Test data cleaned up")
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_db_connection() 