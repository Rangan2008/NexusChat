#!/usr/bin/env python3
"""
Database schema update script
Adds file_content column and removes file_path column for database file storage
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MySQL Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'chatbot'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True
}

def get_db():
    """Get MySQL database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def update_schema():
    """Update the database schema for file storage"""
    try:
        conn = get_db()
        if not conn:
            print("❌ Database connection failed")
            return False
            
        cursor = conn.cursor()
        
        print("🔍 Updating database schema...")
        
        # Check if file_content column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'uploaded_items' 
            AND COLUMN_NAME = 'file_content'
        """, (DB_CONFIG['database'],))
        
        if not cursor.fetchone():
            # Add file_content column
            print("📝 Adding file_content column...")
            cursor.execute("""
                ALTER TABLE uploaded_items 
                ADD COLUMN file_content LONGBLOB AFTER mime_type
            """)
            print("✅ Added file_content column")
        else:
            print("✅ file_content column already exists")
        
        # Check if file_path column exists (to remove it)
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'uploaded_items' 
            AND COLUMN_NAME = 'file_path'
        """, (DB_CONFIG['database'],))
        
        if cursor.fetchone():
            print("🗑️ Removing file_path column...")
            cursor.execute("ALTER TABLE uploaded_items DROP COLUMN file_path")
            print("✅ Removed file_path column")
        else:
            print("✅ file_path column already removed")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("🎉 Database schema updated successfully!")
        print("📁 Files will now be stored in the database instead of filesystem")
        return True
        
    except Exception as e:
        print(f"❌ Schema update error: {e}")
        return False

if __name__ == '__main__':
    print("🔄 Database Schema Update")
    print("========================")
    update_schema()
