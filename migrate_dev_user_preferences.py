#!/usr/bin/env python3
"""
Migration script to add user explanation preference fields to dev database.
Adds health_conditions and dietary_preference columns to users table.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

def main():
    # Load environment variables for dev environment
    load_dotenv('azure-production.env')
    
    # Override with dev database URL
    dev_database_url = "mssql+pyodbc://foodappadmin:DevPass123!Food@food-app-dev-server.database.windows.net:1433/food-app-dev-db?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
    os.environ['DATABASE_URL'] = dev_database_url
    
    # Override with dev-specific database URL if needed
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    # Check if we're targeting a dev database (allow both food-app-dev and foodappsqladmin patterns)
    is_dev_db = 'food-app-dev' in database_url or 'foodappsqladmin' in database_url
    if not is_dev_db:
        print("WARNING: This script is intended for the dev database only")
        print(f"Current DATABASE_URL: {database_url}")
        confirm = input("Continue anyway? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted")
            sys.exit(1)
    
    print(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if columns already exist
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            print(f"Current columns in users table: {columns}")
            
            # Add health_conditions column if it doesn't exist
            if 'health_conditions' not in columns:
                print("Adding health_conditions column...")
                conn.execute(text("ALTER TABLE users ADD health_conditions NTEXT"))
                conn.commit()
                print("✓ health_conditions column added")
            else:
                print("✓ health_conditions column already exists")
            
            # Add dietary_preference column if it doesn't exist
            if 'dietary_preference' not in columns:
                print("Adding dietary_preference column...")
                conn.execute(text("ALTER TABLE users ADD dietary_preference NVARCHAR(50)"))
                conn.commit()
                # Set default value for existing rows
                conn.execute(text("UPDATE users SET dietary_preference = 'none' WHERE dietary_preference IS NULL"))
                conn.commit()
                print("✓ dietary_preference column added")
            else:
                print("✓ dietary_preference column already exists")
            
            # Verify the changes
            inspector = inspect(engine)
            updated_columns = [col['name'] for col in inspector.get_columns('users')]
            print(f"Updated columns in users table: {updated_columns}")
            
            print("\nMigration completed successfully!")
            
    except Exception as e:
        print(f"ERROR: Migration failed - {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()