#!/usr/bin/env python3
"""
Create scan_comments table for multiple timestamped comments per scan.
This script adds the new ScanComment table to support multiple comments with timestamps.
"""

import os
import sys
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import app, db
from models import ScanComment

def create_scan_comments_table():
    """Create the scan_comments table."""
    try:
        with app.app_context():
            print("Creating scan_comments table...")
            
            # Create the table if it doesn't exist
            db.create_all()
            
            print("✅ scan_comments table created successfully!")
            
            # Show table info
            print("\nTable schema:")
            print("- id: Primary key")
            print("- scan_id: Foreign key to scans table")
            print("- comment_text: Text of the comment")
            print("- timestamp: When the comment was created")
            print("- created_at: Created timestamp")
            
    except Exception as e:
        print(f"❌ Error creating scan_comments table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Adding ScanComment table for multiple timestamped comments...")
    
    if create_scan_comments_table():
        print("\n✅ Database migration completed successfully!")
        print("Users can now add multiple timestamped comments to their scans.")
    else:
        print("\n❌ Database migration failed!")
        sys.exit(1)