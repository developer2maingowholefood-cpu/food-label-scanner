#!/usr/bin/env python3
"""
Script to query SQLite database and check if scans are being saved.
Uses correct column names from the actual table structure.
"""

import sqlite3
import json
import os
from datetime import datetime

def query_sqlite_scans():
    """Query SQLite database for scan data"""
    
    # Path to SQLite database
    db_path = "/app/instance/local.db"
    
    print(f"🔍 Checking SQLite Database: {db_path}")
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("✅ Connected to SQLite Database")
        
        # Check if scans table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='scans'
        """)
        
        if not cursor.fetchone():
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
        
        # Get recent scans with correct column names
        cursor.execute("""
            SELECT 
                id, 
                user_id, 
                scan_data,
                timestamp,
                comments,
                image_url,
                blob_name
            FROM scans 
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        recent_scans = cursor.fetchall()
        
        print(f"\n📝 Recent scans (last 10):")
        print("-" * 80)
        for scan in recent_scans:
            scan_id, user_id, scan_data, timestamp, comments, image_url, blob_name = scan
            print(f"ID: {scan_id}")
            print(f"User ID: {user_id}")
            print(f"Timestamp: {timestamp}")
            print(f"Image URL: {image_url}")
            print(f"Blob Name: {blob_name}")
            print(f"Comments: {comments}")
            
            # Parse scan_data JSON if it exists
            if scan_data:
                try:
                    data = json.loads(scan_data)
                    print(f"Scan Data:")
                    for key, value in data.items():
                        if key == 'ingredients' and isinstance(value, list):
                            ingredients_text = ', '.join(value)
                            preview = ingredients_text[:100] + "..." if len(ingredients_text) > 100 else ingredients_text
                            print(f"  {key}: {preview}")
                        elif key == 'safety_score':
                            print(f"  {key}: {value}")
                        elif key == 'is_safe':
                            print(f"  {key}: {value}")
                        else:
                            print(f"  {key}: {value}")
                except json.JSONDecodeError:
                    print(f"  Scan Data: {scan_data[:100]}...")
            
            print("-" * 80)
        
        # Get scans from last 24 hours
        cursor.execute("""
            SELECT COUNT(*) 
            FROM scans 
            WHERE timestamp >= datetime('now', '-1 day')
        """)
        
        recent_scans_count = cursor.fetchone()[0]
        print(f"\n📈 Scans in last 24 hours: {recent_scans_count}")
        
        # Check users table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            print(f"👥 Total users in database: {total_users}")
        
        conn.close()
        print("✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    query_sqlite_scans() 