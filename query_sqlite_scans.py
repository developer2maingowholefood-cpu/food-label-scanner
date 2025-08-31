#!/usr/bin/env python3
"""
Script to query SQLite database and check if scans are being saved.
"""

import sqlite3
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
        
        # Get recent scans
        cursor.execute("""
            SELECT 
                id, 
                user_id, 
                image_filename, 
                created_at,
                ingredients_text,
                is_safe,
                safety_score
            FROM scans 
            ORDER BY created_at DESC
            LIMIT 10
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
        
        # Get scans from last 24 hours
        cursor.execute("""
            SELECT COUNT(*) 
            FROM scans 
            WHERE created_at >= datetime('now', '-1 day')
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