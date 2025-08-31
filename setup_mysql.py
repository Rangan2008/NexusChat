#!/usr/bin/env python3
"""
Setup script for NexusChat Flask Application (MySQL Version)
This script helps set up the environment and initialize the MySQL database
"""

import os
import sys
from pathlib import Path
import mysql.connector
from mysql.connector import Error

def create_directories():
    """Create necessary directories"""
    directories = [
        'uploads',
        'static/uploads',  # For web-accessible uploads if needed
        'instance',  # Flask instance folder
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")

def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✓ Created .env file from .env.example")
            print("⚠️  Please edit .env file with your actual configuration values")
        else:
            print("❌ .env.example not found")
    else:
        print("✓ .env file already exists")

def test_mysql_connection():
    """Test MySQL database connection"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'chatbot')
        }
        
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("✅ MySQL connection successful")
            db_info = connection.get_server_info()
            print(f"   MySQL Server version: {db_info}")
            
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            db_name = cursor.fetchone()
            print(f"   Connected to database: {db_name[0]}")
            
            cursor.close()
            connection.close()
            return True
        
    except Error as e:
        print(f"❌ MySQL connection failed: {e}")
        print("\nPlease check:")
        print("1. MySQL server is running")
        print("2. Database 'chatbot' exists")
        print("3. Username and password are correct in .env file")
        print("4. Host and port are correct")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def init_mysql_database():
    """Initialize the MySQL database with additional tables"""
    try:
        # Import the app to trigger database initialization
        from app_mysql import init_database
        
        if init_database():
            print("✅ MySQL database initialized successfully")
            return True
        else:
            print("❌ MySQL database initialization failed")
            return False
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'flask',
        'werkzeug', 
        'google.generativeai',
        'mysql.connector',
        'fitz',  # PyMuPDF
        'PIL',   # Pillow
        'pytesseract',
        'bcrypt',
        'dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            elif package == 'fitz':
                import fitz
            elif package == 'mysql.connector':
                import mysql.connector
            elif package == 'dotenv':
                import dotenv
            else:
                __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is NOT installed")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        print("✓ Tesseract OCR is installed and accessible")
        return True
    except Exception as e:
        print(f"❌ Tesseract OCR issue: {e}")
        print("Please install Tesseract OCR:")
        print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("  macOS: brew install tesseract")
        print("  Linux: apt-get install tesseract-ocr")
        return False

def verify_existing_tables():
    """Verify that the required MySQL tables exist"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'chatbot')
        }
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Check existing tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = ['users', 'chat_sessions', 'messages']
        existing_tables = [table for table in required_tables if table in tables]
        
        print(f"✓ Found existing tables: {existing_tables}")
        
        cursor.close()
        connection.close()
        
        return len(existing_tables) == len(required_tables)
        
    except Exception as e:
        print(f"❌ Table verification failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 NexusChat Flask App Setup (MySQL Version)")
    print("=" * 50)
    
    # Create directories
    print("\n📁 Creating directories...")
    create_directories()
    
    # Create .env file
    print("\n⚙️  Setting up environment...")
    create_env_file()
    
    # Check dependencies
    print("\n📦 Checking dependencies...")
    deps_ok = check_dependencies()
    
    # Check Tesseract
    print("\n🔍 Checking Tesseract OCR...")
    tesseract_ok = check_tesseract()
    
    # Test MySQL connection
    print("\n🗄️  Testing MySQL connection...")
    mysql_ok = test_mysql_connection()
    
    # Verify existing tables
    if mysql_ok:
        print("\n📋 Verifying existing tables...")
        tables_exist = verify_existing_tables()
        
        if tables_exist:
            print("✅ Required tables found in database")
        else:
            print("⚠️  Some required tables are missing")
    else:
        tables_exist = False
    
    # Initialize additional tables
    if deps_ok and mysql_ok:
        print("\n🔧 Initializing additional tables...")
        db_init_ok = init_mysql_database()
    else:
        print("\n❌ Skipping database initialization due to connection issues")
        db_init_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Setup Summary:")
    print(f"   Dependencies: {'✅' if deps_ok else '❌'}")
    print(f"   Tesseract OCR: {'✅' if tesseract_ok else '⚠️'}")
    print(f"   MySQL Connection: {'✅' if mysql_ok else '❌'}")
    print(f"   Database Tables: {'✅' if tables_exist else '⚠️'}")
    print(f"   Additional Setup: {'✅' if db_init_ok else '❌'}")
    
    if deps_ok and mysql_ok and db_init_ok:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Verify your .env file has correct MySQL credentials")
        print("2. Ensure your Gemini API key is set in .env")
        print("3. Run: python app_mysql.py")
    else:
        print("\n⚠️  Setup completed with issues. Please resolve the above problems.")
        if not deps_ok:
            print("   Install missing dependencies: pip install -r requirements.txt")
        if not mysql_ok:
            print("   Fix MySQL connection issues (check .env file)")
        if not tesseract_ok:
            print("   Install Tesseract OCR (optional for image OCR)")

if __name__ == '__main__':
    main()
