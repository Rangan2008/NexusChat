#!/usr/bin/env python3
"""
Database migration script to add active_file_id column to conversations table
Run this script once to update your existing database
"""

import os
import sqlite3
from datetime import datetime

def migrate_database():
    """Add active_file_id column to conversations table if it doesn't exist"""
    
    # Get database path
    db_path = os.path.join('instance', 'chatbot.db')
    
    if not os.path.exists(db_path):
        print("Database file not found. Run the app first to create the database.")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if active_file_id column already exists
        cursor.execute("PRAGMA table_info(conversation)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'active_file_id' in columns:
            print("Migration already completed. active_file_id column exists.")
            return
        
        print("Adding active_file_id column to conversation table...")
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE conversation 
            ADD COLUMN active_file_id INTEGER 
            REFERENCES uploaded_file(id)
        """)
        
        # Commit the changes
        conn.commit()
        
        print("✅ Migration completed successfully!")
        print("The active_file_id column has been added to the conversation table.")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("🔄 Starting database migration...")
    migrate_database()
