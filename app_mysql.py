#!/usr/bin/env python3
"""
Flask App - NexusChat AI Assistant (MySQL Version)
Features:
1. User Authentication
2. Chat Session Management
3. Messaging with AI integration
4. File/Image Upload & Analysis
5. Question Answering based on uploaded content
6. Conversation Continuity
7. Admin/Utility routes
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
import json
import mimetypes
import tempfile
import time
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_from_directory
import google.generativeai as genai
import fitz  # PyMuPDF for PDF processing
from PIL import Image
import pytesseract  # OCR for image text extraction
import io
import base64
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=int(os.getenv('SESSION_LIFETIME_DAYS', 30)))

# Configure Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-gemini-api-key-here')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')  # Updated model name
vision_model = genai.GenerativeModel('gemini-1.5-flash')  # Can handle both text and vision

# MySQL Database Configuration
# Support for both individual config and DATABASE_URL (for Render)
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Parse DATABASE_URL (format: mysql://user:password@host:port/database)
    parsed = urllib.parse.urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': parsed.hostname,
        'port': parsed.port or 3306,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path[1:],  # Remove leading slash
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
        'autocommit': True
    }
else:
    # Individual environment variables (for local development)
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

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE_MB', 16)) * 1024 * 1024  # Convert MB to bytes
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def get_db():
    """Get MySQL database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def safe_delete_temp_file(file_path, max_attempts=5, delay=0.1):
    """Safely delete a temporary file with retry logic for Windows"""
    for attempt in range(max_attempts):
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
            return True
        except (OSError, PermissionError) as e:
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"Failed to delete temp file {file_path} after {max_attempts} attempts: {e}")
                return False
    return False

def init_database():
    """Initialize the MySQL database with additional tables"""
    try:
        conn = get_db()
        if not conn:
            print("Failed to connect to database")
            return False
            
        cursor = conn.cursor()
        
        # Create uploaded_items table (for file upload metadata)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploaded_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                user_id INT NOT NULL,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                file_size BIGINT NOT NULL,
                mime_type VARCHAR(255) NOT NULL,
                file_content LONGBLOB,
                extracted_text LONGTEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create analysis_results table (for AI analysis of uploaded files)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_id INT NOT NULL,
                session_id INT NOT NULL,
                analysis_type VARCHAR(100) NOT NULL,
                summary LONGTEXT,
                key_points LONGTEXT,
                analysis_data LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES uploaded_items(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        ''')
        
        # Add additional columns to users table if they don't exist
        try:
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN avatar VARCHAR(255) DEFAULT '/static/Avatar.jpeg',
                ADD COLUMN theme VARCHAR(20) DEFAULT 'light',
                ADD COLUMN language VARCHAR(10) DEFAULT 'en',
                ADD COLUMN notifications BOOLEAN DEFAULT TRUE,
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ''')
        except Error as e:
            # Columns might already exist, which is fine
            if "Duplicate column name" not in str(e):
                print(f"Warning: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized successfully")
        return True
        
    except Error as e:
        print(f"❌ Database initialization error: {e}")
        return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from PDF using PyMuPDF"""
    doc = None
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""
    finally:
        if doc:
            doc.close()

def extract_text_from_image(file_path):
    """Extract text from image using OCR"""
    image = None
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"Error extracting image text: {e}")
        return ""
    finally:
        if image:
            image.close()

def analyze_image_with_vision(file_path, user_prompt="Describe what you see in this image"):
    """Analyze image content using Gemini Vision model"""
    try:
        # Open and process the image
        image = Image.open(file_path)
        
        # Convert image to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create the prompt for vision analysis
        vision_prompt = f"""You are an advanced AI vision assistant. Please analyze this image and provide:

1. **Main Description**: What do you see in this image?
2. **Objects/Elements**: List the key objects, people, or elements present
3. **Scene/Setting**: Describe the environment or setting
4. **Colors & Composition**: Notable colors, lighting, and visual composition
5. **Text Content**: Any text visible in the image (if any)
6. **Additional Insights**: Interesting details, mood, or context

User's specific request: {user_prompt}

Please be detailed, accurate, and helpful in your analysis."""
        
        # Generate content using vision model
        response = vision_model.generate_content([vision_prompt, image])
        
        return {
            'success': True,
            'analysis': response.text,
            'type': 'vision_analysis'
        }
        
    except Exception as e:
        print(f"Vision analysis error: {e}")
        return {
            'success': False,
            'analysis': f"Unable to analyze the image visually. Error: {str(e)}",
            'type': 'vision_error'
        }
    finally:
        if 'image' in locals():
            image.close()

def get_ai_response(prompt, context=""):
    """Get response from Gemini AI"""
    try:
        # Create a conversational system prompt
        system_prompt = """You are NexusChat, a helpful and friendly AI assistant. You should:
- Respond naturally and conversationally like a helpful friend
- Be warm, engaging, and personable in your responses
- Answer questions directly and helpfully
- If someone greets you (like "hi", "hello", "how are you"), respond naturally like a human would
- Keep responses concise but informative
- Don't over-analyze simple greetings or casual conversation
- Be supportive and encouraging

Remember: You're having a conversation, not analyzing text or providing academic explanations."""
        
        if context:
            full_prompt = f"{system_prompt}\n\nPrevious conversation context: {context}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        
        print(f"🤖 Sending request to Gemini AI...")
        print(f"📝 API Key configured: {'Yes' if GEMINI_API_KEY and GEMINI_API_KEY != 'your-gemini-api-key-here' else 'No'}")
        
        response = model.generate_content(full_prompt)
        
        if response.text:
            print(f"✅ AI response received successfully")
            return response.text
        else:
            print(f"❌ Empty response from AI")
            return "I received an empty response. Please try rephrasing your question."
            
    except Exception as e:
        print(f"❌ AI response error: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        
        # Check for common API issues
        error_msg = str(e).lower()
        if 'not found' in error_msg or '404' in error_msg:
            return "I apologize, but I'm having trouble connecting to the AI service: Model not found. Please check the API configuration."
        elif 'permission' in error_msg or '403' in error_msg:
            return "I apologize, but there's an API permission issue. Please check your API key."
        elif 'quota' in error_msg or 'limit' in error_msg:
            return "I apologize, but the API quota has been exceeded. Please try again later."
        elif 'key' in error_msg or 'auth' in error_msg:
            return "I apologize, but there's an authentication issue with the AI service."
        else:
            return f"I apologize, but I'm having trouble connecting to the AI service: {str(e)[:100]}"

def get_ai_analysis(text_content, file_type):
    """Get AI analysis of uploaded content"""
    try:
        if file_type.lower() == 'pdf':
            prompt = f"""Analyze this PDF content and provide:
1. A concise summary (2-3 sentences)
2. Key points (bullet format)
3. Main topics covered
4. Any important data or insights

Content: {text_content}"""
        else:  # Image
            prompt = f"""Analyze this text extracted from an image and provide:
1. A summary of what was found
2. Key information identified
3. Any structured data or important details

Extracted text: {text_content}"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI analysis error: {e}")
        return "Unable to analyze the content at this time."

# Authentication decorator
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES ====================

# Static file serving
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ==================== TEMPLATE ROUTES ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('chat_page'))
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    """Signup page"""
    if 'user_id' in session:
        return redirect(url_for('chat_page'))
    return render_template('signup.html')

@app.route('/chat')
@login_required
def chat_page():
    """Chat interface page"""
    return render_template('chat.html')

@app.route('/profile')
@login_required
def profile_page():
    """User profile page"""
    return render_template('profile.html')

# ==================== AUTHENTICATION API ====================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """User registration"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400
        
        if len(username) < 3 or len(username) > 50:
            return jsonify({'error': 'Username must be 3-50 characters'}), 400
        
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Check if user already exists
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400
        
        # Create user
        password_hash = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
            (username, email, password_hash)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Account created successfully'}), 201
    
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Check credentials
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            session.permanent = True
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

# ==================== USER PROFILE API ====================

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile information"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.username, u.email, u.avatar, u.theme, u.language, u.notifications, 
                   u.date_created, COUNT(cs.id) as total_chats
            FROM users u
            LEFT JOIN chat_sessions cs ON u.id = cs.user_id
            WHERE u.id = %s
            GROUP BY u.id
        ''', (session['user_id'],))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify({
                'username': user[0],
                'email': user[1],
                'avatar': user[2] or '/static/Avatar.jpeg',
                'theme': user[3] or 'light',
                'language': user[4] or 'en',
                'notifications': bool(user[5]),
                'joined_date': user[6].strftime('%Y-%m-%d') if user[6] else '',
                'total_chats': user[7] or 0
            }), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    
    except Exception as e:
        print(f"Profile fetch error: {e}")
        return jsonify({'error': 'Failed to fetch profile'}), 500

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        theme = data.get('theme', 'light')
        language = data.get('language', 'en')
        notifications = data.get('notifications', True)
        
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Check if username/email is taken by another user
        cursor.execute(
            'SELECT id FROM users WHERE (username = %s OR email = %s) AND id != %s',
            (username, email, session['user_id'])
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Username or email already taken'}), 400
        
        # Update user data
        if password:
            if len(password) < 8:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            password_hash = generate_password_hash(password)
            cursor.execute('''
                UPDATE users 
                SET email = %s, username = %s, password_hash = %s, theme = %s, 
                    language = %s, notifications = %s
                WHERE id = %s
            ''', (email, username, password_hash, theme, language, notifications, session['user_id']))
        else:
            cursor.execute('''
                UPDATE users 
                SET email = %s, username = %s, theme = %s, language = %s, notifications = %s
                WHERE id = %s
            ''', (email, username, theme, language, notifications, session['user_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Update session
        session['username'] = username
        
        return jsonify({'message': 'Profile updated successfully'}), 200
    
    except Exception as e:
        print(f"Profile update error: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500

# ==================== CHAT SESSION MANAGEMENT ====================

@app.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get all chat sessions for the user"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute('''
            SELECT cs.id, cs.session_name as title, cs.created_at, cs.updated_at,
                   COUNT(m.id) as message_count,
                   (SELECT content FROM messages WHERE session_id = cs.id ORDER BY timestamp DESC LIMIT 1) as last_message
            FROM chat_sessions cs
            LEFT JOIN messages m ON cs.id = m.session_id
            WHERE cs.user_id = %s
            GROUP BY cs.id
            ORDER BY cs.updated_at DESC
        ''', (session['user_id'],))
        
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        sessions_list = []
        for session_data in sessions:
            sessions_list.append({
                'id': session_data[0],
                'title': session_data[1],
                'created_at': session_data[2].strftime('%Y-%m-%d %H:%M:%S') if session_data[2] else '',
                'updated_at': session_data[3].strftime('%Y-%m-%d %H:%M:%S') if session_data[3] else '',
                'message_count': session_data[4] or 0,
                'last_message': session_data[5]
            })
        
        return jsonify({'sessions': sessions_list}), 200
    
    except Exception as e:
        print(f"Sessions fetch error: {e}")
        return jsonify({'error': 'Failed to fetch sessions'}), 500

@app.route('/api/new_session', methods=['POST'])
@login_required
def create_new_session():
    """Create a new chat session"""
    try:
        data = request.get_json() or {}
        title = data.get('title', 'New Chat')
        
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO chat_sessions (user_id, session_name) VALUES (%s, %s)',
            (session['user_id'], title)
        )
        session_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'session_id': session_id,
            'title': title,
            'message': 'New session created'
        }), 201
    
    except Exception as e:
        print(f"Session creation error: {e}")
        return jsonify({'error': 'Failed to create session'}), 500

@app.route('/api/session/<int:session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """Get session details with messages and uploaded items"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session belongs to user
        cursor.execute(
            'SELECT id, session_name, created_at FROM chat_sessions WHERE id = %s AND user_id = %s',
            (session_id, session['user_id'])
        )
        session_data = cursor.fetchone()
        
        if not session_data:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        # Get messages
        cursor.execute('''
            SELECT id, sender, content, timestamp 
            FROM messages 
            WHERE session_id = %s 
            ORDER BY timestamp ASC
        ''', (session_id,))
        messages = cursor.fetchall()
        
        # Get uploaded items
        cursor.execute('''
            SELECT id, original_filename, file_type, file_size, uploaded_at
            FROM uploaded_items 
            WHERE session_id = %s
            ORDER BY uploaded_at DESC
        ''', (session_id,))
        uploaded_items = cursor.fetchall()
        
        # Get analysis results
        cursor.execute('''
            SELECT a.id, a.item_id, a.analysis_type, a.summary, a.key_points, a.created_at,
                   u.original_filename
            FROM analysis_results a
            JOIN uploaded_items u ON a.item_id = u.id
            WHERE a.session_id = %s
            ORDER BY a.created_at DESC
        ''', (session_id,))
        analyses = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'session': {
                'id': session_data[0],
                'title': session_data[1],
                'created_at': session_data[2].strftime('%Y-%m-%d %H:%M:%S') if session_data[2] else ''
            },
            'messages': [
                {
                    'id': msg[0],
                    'sender': msg[1], 
                    'content': msg[2],
                    'timestamp': msg[3].strftime('%Y-%m-%d %H:%M:%S') if msg[3] else ''
                } for msg in messages
            ],
            'uploaded_items': [
                {
                    'id': item[0],
                    'original_filename': item[1],
                    'file_type': item[2],
                    'file_size': item[3],
                    'uploaded_at': item[4].strftime('%Y-%m-%d %H:%M:%S') if item[4] else ''
                } for item in uploaded_items
            ],
            'analyses': [
                {
                    'id': analysis[0],
                    'item_id': analysis[1],
                    'analysis_type': analysis[2],
                    'summary': analysis[3],
                    'key_points': analysis[4],
                    'created_at': analysis[5].strftime('%Y-%m-%d %H:%M:%S') if analysis[5] else '',
                    'filename': analysis[6]
                } for analysis in analyses
            ]
        }), 200
    
    except Exception as e:
        print(f"Session fetch error: {e}")
        return jsonify({'error': 'Failed to fetch session'}), 500

@app.route('/api/delete_session/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    """Delete a chat session and all related data"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session belongs to user
        cursor.execute(
            'SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s',
            (session_id, session['user_id'])
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        # Delete session (cascade will handle related records)
        cursor.execute('DELETE FROM chat_sessions WHERE id = %s', (session_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Session deleted successfully'}), 200
    
    except Exception as e:
        print(f"Session deletion error: {e}")
        return jsonify({'error': 'Failed to delete session'}), 500

# ==================== MESSAGING API ====================

@app.route('/api/message', methods=['POST'])
@login_required
def send_message():
    """Send a message and get AI response"""
    try:
        print("🔍 /api/message route called")
        data = request.get_json()
        print(f"📨 Request data: {data}")
        
        session_id = data.get('session_id')
        sender = data.get('sender', 'user')
        content = data.get('content', '').strip()
        file_id = data.get('file_id')
        
        print(f"📝 Session ID: {session_id}, Content: '{content[:50]}...', File ID: {file_id}")
        
        if not session_id or not content:
            print("❌ Missing session_id or content")
            return jsonify({'error': 'Session ID and content required'}), 400
        
        conn = get_db()
        if not conn:
            print("❌ Database connection failed")
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session belongs to user
        cursor.execute(
            'SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s',
            (session_id, session['user_id'])
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            print("❌ Session not found or doesn't belong to user")
            return jsonify({'error': 'Session not found'}), 404
        
        print("✅ Session verified, saving user message...")
        
        # Save user message
        cursor.execute(
            'INSERT INTO messages (session_id, sender, content) VALUES (%s, %s, %s)',
            (session_id, 'user', content)
        )
        
        # Get recent conversation context
        cursor.execute('''
            SELECT sender, content FROM messages 
            WHERE session_id = %s 
            ORDER BY timestamp DESC LIMIT 10
        ''', (session_id,))
        recent_messages = cursor.fetchall()
        
        # Build context from recent messages
        context_parts = []
        for msg in reversed(recent_messages):
            role = "Human" if msg[0] == 'user' else "Assistant"
            context_parts.append(f"{role}: {msg[1]}")
        conversation_context = "\n".join(context_parts)
        
        # Add file content if file_id is provided
        file_content = ""
        if file_id:
            print(f"🔍 Looking up file content for file_id: {file_id}")
            cursor.execute('''
                SELECT original_filename, extracted_text, file_type 
                FROM uploaded_items 
                WHERE id = %s AND session_id = %s AND user_id = %s
            ''', (file_id, session_id, session['user_id']))
            
            file_data = cursor.fetchone()
            if file_data:
                filename, extracted_text, file_type = file_data
                print(f"📄 Found file: {filename} ({file_type}) with {len(extracted_text)} chars of text")
                
                # Get vision analysis if it's an image
                vision_context = ""
                if file_type == 'image':
                    cursor.execute('''
                        SELECT summary FROM analysis_results 
                        WHERE item_id = %s AND analysis_type IN ('vision_analysis', 'custom_vision_analysis')
                        ORDER BY created_at DESC LIMIT 1
                    ''', (file_id,))
                    
                    vision_result = cursor.fetchone()
                    if vision_result:
                        vision_context = f"\n\nImage Visual Analysis:\n{vision_result[0]}"
                
                file_content = f"\n\nUploaded File Context:\nFile: {filename}\nType: {file_type}"
                if extracted_text.strip():
                    file_content += f"\nExtracted Text: {extracted_text}"
                file_content += vision_context
            else:
                print(f"❌ File not found for file_id: {file_id}")
        
        # Combine conversation context and file content
        full_context = conversation_context + file_content
        
        print(f"🧠 Calling AI with context length: {len(full_context)} chars")
        
        # Get AI response
        ai_response = get_ai_response(content, full_context)
        
        print(f"🤖 AI response received: '{ai_response[:100]}...'")
        
        # Save AI response
        cursor.execute(
            'INSERT INTO messages (session_id, sender, content) VALUES (%s, %s, %s)',
            (session_id, 'assistant', ai_response)
        )
        
        # Update session timestamp
        cursor.execute(
            'UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s',
            (session_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Message processed successfully")
        
        return jsonify({
            'user_message': content,
            'ai_message': ai_response,
            'session_id': session_id
        }), 200
    
    except Exception as e:
        print(f"Message error: {e}")
        return jsonify({'error': 'Failed to process message'}), 500

@app.route('/api/messages/<int:session_id>', methods=['GET'])
@login_required
def get_messages(session_id):
    """Get all messages for a session"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session belongs to user
        cursor.execute(
            'SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s',
            (session_id, session['user_id'])
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        cursor.execute('''
            SELECT id, sender, content, timestamp 
            FROM messages 
            WHERE session_id = %s 
            ORDER BY timestamp ASC
        ''', (session_id,))
        
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'messages': [
                {
                    'id': msg[0],
                    'sender': msg[1],
                    'content': msg[2],
                    'timestamp': msg[3].strftime('%Y-%m-%d %H:%M:%S') if msg[3] else ''
                } for msg in messages
            ]
        }), 200
    
    except Exception as e:
        print(f"Messages fetch error: {e}")
        return jsonify({'error': 'Failed to fetch messages'}), 500

# ==================== FILE UPLOAD & ANALYSIS ====================

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """Upload and analyze a file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        session_id = request.form.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session belongs to user
        cursor.execute(
            'SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s',
            (session_id, session['user_id'])
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        # Read file content into memory
        file.seek(0)  # Reset file pointer
        file_content = file.read()
        file_size = len(file_content)
        mime_type = mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
        
        # Extract text based on file type
        extracted_text = ""
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        
        if file_ext == 'pdf':
            # Create temporary file for PDF processing
            temp_file = None
            try:
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                temp_file.write(file_content)
                temp_file.flush()
                temp_file.close()  # Close file handle before processing
                extracted_text = extract_text_from_pdf(temp_file.name)
            finally:
                if temp_file:
                    safe_delete_temp_file(temp_file.name)
            file_type = 'pdf'
        elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            # Create temporary file for image processing
            temp_file = None
            try:
                temp_file = tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False)
                temp_file.write(file_content)
                temp_file.flush()
                temp_file.close()  # Close file handle before processing
                
                # Extract text using OCR
                extracted_text = extract_text_from_image(temp_file.name)
                
                # Perform vision analysis
                vision_analysis = analyze_image_with_vision(temp_file.name)
                
            finally:
                if temp_file:
                    safe_delete_temp_file(temp_file.name)
            file_type = 'image'
        else:
            file_type = 'other'
        
        # Generate unique filename for database storage
        filename = f"{session['user_id']}_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
        
        # Save file metadata and content to database
        cursor.execute('''
            INSERT INTO uploaded_items 
            (session_id, user_id, filename, original_filename, file_type, file_size, mime_type, file_content, extracted_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (session_id, session['user_id'], filename, original_filename, file_type, file_size, mime_type, file_content, extracted_text))
        
        item_id = cursor.lastrowid
        
        # Generate AI analysis
        analysis_results = []
        
        # Text-based analysis (for PDFs and OCR text)
        if extracted_text.strip():
            text_analysis = get_ai_analysis(extracted_text, file_type)
            
            cursor.execute('''
                INSERT INTO analysis_results (item_id, session_id, analysis_type, summary)
                VALUES (%s, %s, %s, %s)
            ''', (item_id, session_id, f'{file_type}_text_analysis', text_analysis))
            
            analysis_results.append({
                'type': 'text_analysis',
                'content': text_analysis
            })
        
        # Vision analysis (for images)
        if file_type == 'image' and 'vision_analysis' in locals():
            cursor.execute('''
                INSERT INTO analysis_results (item_id, session_id, analysis_type, summary)
                VALUES (%s, %s, %s, %s)
            ''', (item_id, session_id, 'vision_analysis', vision_analysis['analysis']))
            
            analysis_results.append({
                'type': 'vision_analysis',
                'content': vision_analysis['analysis'],
                'success': vision_analysis['success']
            })
        
        # Update session timestamp
        cursor.execute(
            'UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s',
            (session_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Prepare response data
        response_data = {
            'message': 'File uploaded and analyzed successfully',
            'file_id': item_id,
            'filename': original_filename,
            'file_type': file_type,
            'analyses': analysis_results
        }
        
        # Include extracted text preview for text-based files
        if extracted_text.strip():
            response_data['extracted_text'] = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
        
        # Include vision analysis preview for images
        if file_type == 'image' and 'vision_analysis' in locals() and vision_analysis['success']:
            response_data['vision_preview'] = vision_analysis['analysis'][:300] + "..." if len(vision_analysis['analysis']) > 300 else vision_analysis['analysis']
        
        response_data['analysis_available'] = len(analysis_results) > 0
        
        return jsonify(response_data), 200
    
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': 'Failed to upload file'}), 500

@app.route('/api/analyze_image/<int:file_id>', methods=['POST'])
@login_required
def analyze_specific_image(file_id):
    """Analyze a specific uploaded image with custom prompt"""
    try:
        data = request.get_json()
        custom_prompt = data.get('prompt', 'Describe what you see in this image')
        
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Get the image file data
        cursor.execute('''
            SELECT ui.file_content, ui.original_filename, ui.file_type, ui.session_id
            FROM uploaded_items ui
            WHERE ui.id = %s AND ui.user_id = %s AND ui.file_type = 'image'
        ''', (file_id, session['user_id']))
        
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Image not found'}), 404
        
        file_content, original_filename, file_type, session_id = result
        
        # Create temporary file for analysis
        temp_file = None
        try:
            file_ext = original_filename.rsplit('.', 1)[1].lower()
            temp_file = tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False)
            temp_file.write(file_content)
            temp_file.flush()
            temp_file.close()
            
            # Perform vision analysis with custom prompt
            vision_analysis = analyze_image_with_vision(temp_file.name, custom_prompt)
            
            if vision_analysis['success']:
                # Save the new analysis to database
                cursor.execute('''
                    INSERT INTO analysis_results (item_id, session_id, analysis_type, summary)
                    VALUES (%s, %s, %s, %s)
                ''', (file_id, session_id, 'custom_vision_analysis', vision_analysis['analysis']))
                
                conn.commit()
                
        finally:
            if temp_file:
                safe_delete_temp_file(temp_file.name)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': vision_analysis['success'],
            'analysis': vision_analysis['analysis'],
            'prompt_used': custom_prompt,
            'filename': original_filename
        }), 200
        
    except Exception as e:
        print(f"Custom image analysis error: {e}")
        return jsonify({'error': 'Failed to analyze image'}), 500

@app.route('/api/analyses/<int:session_id>', methods=['GET'])
@login_required
def get_analyses(session_id):
    """Get all file analyses for a session"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session belongs to user
        cursor.execute(
            'SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s',
            (session_id, session['user_id'])
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        cursor.execute('''
            SELECT a.id, a.item_id, a.analysis_type, a.summary, a.key_points, a.created_at,
                   u.original_filename, u.file_type
            FROM analysis_results a
            JOIN uploaded_items u ON a.item_id = u.id
            WHERE a.session_id = %s
            ORDER BY a.created_at DESC
        ''', (session_id,))
        
        analyses = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'analyses': [
                {
                    'id': analysis[0],
                    'item_id': analysis[1],
                    'analysis_type': analysis[2],
                    'summary': analysis[3],
                    'key_points': analysis[4],
                    'created_at': analysis[5].strftime('%Y-%m-%d %H:%M:%S') if analysis[5] else '',
                    'filename': analysis[6],
                    'file_type': analysis[7]
                } for analysis in analyses
            ]
        }), 200
    
    except Exception as e:
        print(f"Analyses fetch error: {e}")
        return jsonify({'error': 'Failed to fetch analyses'}), 500

@app.route('/api/ask_about_file', methods=['POST'])
@login_required
def ask_about_file():
    """Ask a question about an uploaded file"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        item_id = data.get('item_id')
        question = data.get('question', '').strip()
        
        if not session_id or not item_id or not question:
            return jsonify({'error': 'Session ID, item ID, and question required'}), 400
        
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session and item belong to user
        cursor.execute('''
            SELECT u.extracted_text, u.original_filename, u.file_type, a.summary
            FROM uploaded_items u
            LEFT JOIN analysis_results a ON u.id = a.item_id
            JOIN chat_sessions s ON u.session_id = s.id
            WHERE u.id = %s AND u.session_id = %s AND s.user_id = %s
        ''', (item_id, session_id, session['user_id']))
        
        file_data = cursor.fetchone()
        if not file_data:
            cursor.close()
            conn.close()
            return jsonify({'error': 'File not found'}), 404
        
        # Build context for AI
        context = f"File: {file_data[1]}\n"
        if file_data[3]:
            context += f"Analysis: {file_data[3]}\n"
        if file_data[0]:
            context += f"Content: {file_data[0]}\n"
        
        # Get AI response
        ai_response = get_ai_response(question, context)
        
        # Save the question and answer as messages
        cursor.execute(
            'INSERT INTO messages (session_id, sender, content) VALUES (%s, %s, %s)',
            (session_id, 'user', f"Question about {file_data[1]}: {question}")
        )
        
        cursor.execute(
            'INSERT INTO messages (session_id, sender, content) VALUES (%s, %s, %s)',
            (session_id, 'assistant', ai_response)
        )
        
        # Update session timestamp
        cursor.execute(
            'UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s',
            (session_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'question': question,
            'answer': ai_response,
            'filename': file_data[1]
        }), 200
    
    except Exception as e:
        print(f"File question error: {e}")
        return jsonify({'error': 'Failed to process question'}), 500

@app.route('/api/delete_item/<int:item_id>', methods=['DELETE'])
@login_required
def delete_uploaded_item(item_id):
    """Delete an uploaded item"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify item belongs to user  
        cursor.execute('''
            SELECT u.id 
            FROM uploaded_items u
            JOIN chat_sessions s ON u.session_id = s.id
            WHERE u.id = %s AND s.user_id = %s
        ''', (item_id, session['user_id']))
        
        item = cursor.fetchone()
        if not item:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Item not found'}), 404
        
        # Delete from database (cascade will handle analysis_results)
        # No filesystem cleanup needed since files are stored in database
        cursor.execute('DELETE FROM uploaded_items WHERE id = %s', (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Item deleted successfully'}), 200
    
    except Exception as e:
        print(f"Item deletion error: {e}")
        return jsonify({'error': 'Failed to delete item'}), 500

# ==================== CHAT SEARCH ====================

@app.route('/api/chats/search', methods=['GET'])
@login_required
def search_chats():
    """Search through chat messages"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'results': []}), 200
            
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Search in messages content and session names
        search_pattern = f"%{query}%"
        cursor.execute('''
            SELECT DISTINCT cs.id, cs.session_name, m.content, m.timestamp, m.sender
            FROM chat_sessions cs
            LEFT JOIN messages m ON cs.id = m.session_id
            WHERE cs.user_id = %s 
            AND (m.content LIKE %s OR cs.session_name LIKE %s)
            ORDER BY m.timestamp DESC
            LIMIT 20
        ''', (session['user_id'], search_pattern, search_pattern))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        search_results = []
        for result in results:
            session_id, session_name, content, timestamp, sender = result
            search_results.append({
                'session_id': session_id,
                'session_name': session_name,
                'content': content,
                'timestamp': timestamp.isoformat() if timestamp else '',
                'sender': sender
            })
        
        return jsonify({'results': search_results}), 200
    
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': 'Search failed'}), 500

# ==================== CHAT EXPORT ====================

@app.route('/api/chats/export', methods=['GET'])
@login_required
def export_chat_history():
    """Export all chat history for the user"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Get all sessions for the user
        cursor.execute('''
            SELECT cs.id, cs.session_name, cs.created_at, cs.updated_at
            FROM chat_sessions cs
            WHERE cs.user_id = %s
            ORDER BY cs.created_at DESC
        ''', (session['user_id'],))
        
        sessions = cursor.fetchall()
        export_data = {
            'export_date': datetime.now().isoformat(),
            'user_id': session['user_id'],
            'total_sessions': len(sessions),
            'sessions': []
        }
        
        for sess in sessions:
            session_id, session_name, created_at, updated_at = sess
            
            # Get messages for this session
            cursor.execute('''
                SELECT sender, content, timestamp
                FROM messages
                WHERE session_id = %s
                ORDER BY timestamp ASC
            ''', (session_id,))
            
            messages = cursor.fetchall()
            
            # Get uploaded files for this session
            cursor.execute('''
                SELECT original_filename, file_type, uploaded_at
                FROM uploaded_items
                WHERE session_id = %s
                ORDER BY uploaded_at ASC
            ''', (session_id,))
            
            files = cursor.fetchall()
            
            session_data = {
                'session_id': session_id,
                'session_name': session_name,
                'created_at': created_at.isoformat() if created_at else None,
                'updated_at': updated_at.isoformat() if updated_at else None,
                'messages': [
                    {
                        'sender': msg[0],
                        'content': msg[1],
                        'timestamp': msg[2].isoformat() if msg[2] else None
                    } for msg in messages
                ],
                'uploaded_files': [
                    {
                        'filename': file[0],
                        'file_type': file[1],
                        'uploaded_at': file[2].isoformat() if file[2] else None
                    } for file in files
                ]
            }
            
            export_data['sessions'].append(session_data)
        
        cursor.close()
        conn.close()
        
        return jsonify(export_data), 200
    
    except Exception as e:
        print(f"Export error: {e}")
        return jsonify({'error': 'Failed to export chat history'}), 500

@app.route('/api/session/<int:session_id>/update-name', methods=['PUT'])
@login_required
def update_session_name(session_id):
    """Update session name"""
    try:
        data = request.get_json()
        new_name = data.get('session_name', '').strip()
        
        if not new_name:
            return jsonify({'error': 'Session name required'}), 400
            
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Verify session belongs to user and update only if it's currently "New Chat"
        cursor.execute('''
            UPDATE chat_sessions 
            SET session_name = %s 
            WHERE id = %s AND user_id = %s AND session_name = 'New Chat'
        ''', (new_name, session_id, session['user_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Session name updated'}), 200
    
    except Exception as e:
        print(f"Session name update error: {e}")
        return jsonify({'error': 'Failed to update session name'}), 500

# ==================== LEGACY API ROUTES (for compatibility) ====================

@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Legacy route - redirects to sessions"""
    return get_sessions()

@app.route('/api/chats', methods=['GET'])
@login_required  
def get_chats():
    """Legacy route for checking authentication"""
    return jsonify({'status': 'authenticated', 'user_id': session['user_id']}), 200

@app.route('/api/chat', methods=['POST'])
@login_required
def legacy_chat():
    """Legacy chat route - creates session if needed"""
    try:
        data = request.get_json()
        user_message = data.get('user_message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message required'}), 400
        
        # Create a new session for this chat
        conn = get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO chat_sessions (user_id, session_name) VALUES (%s, %s)',
            (session['user_id'], user_message[:50] + "..." if len(user_message) > 50 else user_message)
        )
        session_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        # Process the message
        message_data = {
            'session_id': session_id,
            'content': user_message
        }
        
        # Use the existing message endpoint
        request.get_json = lambda: message_data
        return send_message()
    
    except Exception as e:
        print(f"Legacy chat error: {e}")
        return jsonify({'error': 'Failed to process chat'}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    if request.is_json:
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.is_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({'error': 'File too large'}), 413

# ==================== INITIALIZATION ====================

if __name__ == '__main__':
    # Test database connection
    print("🔍 Testing MySQL connection...")
    test_conn = get_db()
    if test_conn:
        print("✅ MySQL connection successful")
        test_conn.close()
        
        # Initialize database
        if init_database():
            print("✅ Database initialization complete")
        else:
            print("❌ Database initialization failed")
            exit(1)
    else:
        print("❌ MySQL connection failed")
        print("Please check your database configuration in .env file")
        exit(1)
    
    print("🚀 NexusChat Flask App Starting...")
    print(f"🗄️ Database: MySQL ({DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']})")
    print(f"🔑 Session lifetime: {app.config['PERMANENT_SESSION_LIFETIME']}")
    print("📁 File storage: Database (no filesystem dependency)")
    
    # Run the app
    if __name__ == '__main__':
        # For production (Heroku, Railway, etc.)
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        app.run(host='0.0.0.0', port=port, debug=debug)
    else:
        # For local development
        app.run(debug=True, host='0.0.0.0', port=5000)
