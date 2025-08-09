import os
import re
import io
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import PyPDF2
from PIL import Image
import pytesseract
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key'),
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///chatbot.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=512* 1024 * 1024,
    ALLOWED_EXTENSIONS={'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'},
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000')}})

# Optional: Configure Tesseract path
try:
    pytesseract.pytesseract.tesseract_cmd = os.environ.get('TESSERACT_CMD', '/usr/bin/tesseract')
except:
    print("Tesseract OCR not configured properly")

# ========== ROUTES FOR PAGES ==========
@app.route('/')
def home():
    return render_template('index.html')  # ✅ shows landing page

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/chat')
@login_required
def chat_page():
    return render_template('chat.html')

# ========== USER MODEL ==========
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(255), default='/static/Avatar.jpeg')
    avatar_data = db.Column(db.Text)  # Store base64 encoded avatar data
    avatar_mimetype = db.Column(db.String(50))  # Store MIME type for proper serving
    theme = db.Column(db.String(20), default='light')
    notifications = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(20), default='English')
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')
    files = db.relationship('UploadedFile', backref='user', lazy=True, cascade='all, delete-orphan')

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    is_active = db.Column(db.Boolean, default=True)
    active_file_id = db.Column(db.Integer, db.ForeignKey('uploaded_file.id'), nullable=True)
    chats = db.relationship('Chat', backref='conversation', lazy=True, cascade='all, delete-orphan', order_by='Chat.timestamp')
    active_file = db.relationship('UploadedFile', foreign_keys=[active_file_id])

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    ai_message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    filesize = db.Column(db.Integer, nullable=False)
    extracted_text = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
# ========== HELPER FUNCTIONS ==========    

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_email(email):
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email)

def validate_username(username):
    return re.match(r"^[a-zA-Z0-9_-]{3,32}$", username)

def extract_text_from_pdf(file_stream):
    """Extract text from PDF file stream with improved error handling"""
    try:
        # Ensure we're at the beginning of the stream
        file_stream.seek(0)
        
        # Try to create PdfReader
        reader = PyPDF2.PdfReader(file_stream)
        
        # Check if PDF is encrypted
        if reader.is_encrypted:
            return '[Error: PDF is encrypted and cannot be read]'
        
        # Extract text from all pages
        text_content = []
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_content.append(page_text.strip())
            except Exception as page_error:
                print(f"Warning: Could not extract text from page {page_num + 1}: {page_error}")
                continue
        
        # Join all text content
        full_text = '\n'.join(text_content)
        
        # Return appropriate message based on extraction result
        if full_text.strip():
            return full_text.strip()
        else:
            return '[No extractable text found in PDF - may be image-based or empty]'
            
    except PyPDF2.errors.PdfReadError as e:
        return f'[Error: Invalid or corrupted PDF file - {str(e)}]'
    except Exception as e:
        return f'[Error extracting PDF text: {str(e)}]'

def extract_text_from_image(file_stream):
    """Extract text from image file stream with improved error handling"""
    try:
        # Ensure we're at the beginning of the stream
        file_stream.seek(0)
        
        # Open the image
        image = Image.open(file_stream)
        
        # Convert to RGB if necessary (for better OCR results)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text using pytesseract
        text = pytesseract.image_to_string(image, config='--psm 6')
        
        # Clean up the text
        text = text.strip()
        
        if text:
            return text
        else:
            return '[No text found in image]'
            
    except pytesseract.TesseractNotFoundError:
        return '[Error: Tesseract OCR not found - please install Tesseract]'
    except Exception as e:
        return f'[Error extracting image text: {str(e)}]'

def generate_conversation_title(message):
    """Generate a conversation title from the first message"""
    # Clean and truncate the message for use as a title
    title = re.sub(r'[^\w\s-]', '', message.strip())
    title = ' '.join(title.split()[:8])  # Take first 8 words
    return title[:100] if title else "New Conversation"

def get_or_create_conversation(user_id, conversation_id=None, first_message=""):
    """Get existing conversation or create a new one"""
    if conversation_id:
        # Try to get existing conversation
        conversation = Conversation.query.filter_by(
            id=conversation_id, 
            user_id=user_id,
            is_active=True
        ).first()
        if conversation:
            return conversation
    
    # Create new conversation
    title = generate_conversation_title(first_message)
    conversation = Conversation(
        user_id=user_id,
        title=title,
        is_active=True
    )
    db.session.add(conversation)
    db.session.flush()  # Get the ID without committing
    return conversation

def process_uploaded_file(file):
    """Process uploaded file in memory and extract text without saving to disk"""
    try:
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        print(f"Processing file: {filename} (type: {file_ext})")
        
        # Read file into memory
        file.seek(0)  # Reset file pointer to beginning
        file_data = file.read()
        file_stream = io.BytesIO(file_data)
        
        print(f"File size: {len(file_data)} bytes")
        
        # Extract text based on file type
        if file_ext == 'pdf':
            print("Extracting text from PDF...")
            text = extract_text_from_pdf(file_stream)
        elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            print("Extracting text from image...")
            text = extract_text_from_image(file_stream)
        else:
            text = '[Unsupported file type]'
            print(f"Unsupported file type: {file_ext}")
        
        print(f"Text extraction result length: {len(text)} characters")
        
        return filename, file_ext, len(file_data), text
        
    except Exception as e:
        print(f"Error in process_uploaded_file: {e}")
        import traceback
        traceback.print_exc()
        raise e

def encode_avatar_to_base64(file):
    """Convert uploaded avatar to base64 for database storage"""
    file.seek(0)
    file_data = file.read()
    
    # Optimize image size if it's too large
    if len(file_data) > 1024 * 1024:  # If larger than 1MB
        image = Image.open(io.BytesIO(file_data))
        # Resize to maximum 400x400 while maintaining aspect ratio
        image.thumbnail((400, 400), Image.Resampling.LANCZOS)
        
        # Save optimized image to bytes
        output = io.BytesIO()
        image_format = image.format or 'JPEG'
        image.save(output, format=image_format, quality=85)
        file_data = output.getvalue()
    
    # Encode to base64
    encoded_data = base64.b64encode(file_data).decode('utf-8')
    
    # Determine MIME type
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpeg'
    mime_type = f'image/{file_ext}' if file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else 'image/jpeg'
    
    return encoded_data, mime_type

# ========== API ROUTES ==========

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not all([username, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    if not validate_username(username):
        return jsonify({'error': 'Invalid username format'}), 400
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'Username or email already exists'}), 409

    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    login_user(user)
    return jsonify({'message': 'Login successful'}), 200

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

# ========== PROFILE API ROUTES ==========
@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    user = current_user
    total_chats = Chat.query.filter_by(user_id=user.id).count()
    return jsonify({
        'username': user.username,
        'email': user.email,
        'avatar': user.avatar,
        'theme': user.theme,
        'notifications': user.notifications,
        'language': user.language,
        'joined_date': user.joined_date.strftime('%Y-%m-%d'),
        'total_chats': total_chats
    })

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    user = current_user
    
    # Validate and update email
    email = data.get('email', '').strip().lower()
    if email and email != user.email:
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Email already exists'}), 409
        user.email = email
    
    # Validate and update username
    username = data.get('username', '').strip()
    if username and username != user.username:
        if not validate_username(username):
            return jsonify({'error': 'Invalid username format'}), 400
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Username already exists'}), 409
        user.username = username
    
    # Update password if provided
    password = data.get('password', '').strip()
    if password:
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        user.password_hash = generate_password_hash(password)
    
    # Update preferences
    user.theme = data.get('theme', user.theme)
    user.notifications = data.get('notifications', user.notifications)
    user.language = data.get('language', user.language)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500

@app.route('/api/profile/avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': 'No avatar file provided'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400
    
    try:
        # Process avatar and convert to base64
        avatar_data, mime_type = encode_avatar_to_base64(file)
        
        # Update user's avatar data in database
        current_user.avatar_data = avatar_data
        current_user.avatar_mimetype = mime_type
        current_user.avatar = f'/api/avatar/{current_user.id}'  # Dynamic avatar URL
        db.session.commit()
        
        return jsonify({
            'message': 'Avatar updated successfully',
            'avatar_url': current_user.avatar
        })
    except Exception as e:
        print(f"Avatar upload error: {e}")
        return jsonify({'error': 'Failed to upload avatar'}), 500

@app.route('/api/avatar/<int:user_id>')
def serve_avatar(user_id):
    """Serve user avatar from database"""
    user = User.query.get(user_id)
    if not user or not user.avatar_data:
        # Return default avatar
        default_avatar_path = os.path.join(app.static_folder, 'Avatar.jpeg')
        if os.path.exists(default_avatar_path):
            with open(default_avatar_path, 'rb') as f:
                avatar_data = f.read()
            return Response(avatar_data, mimetype='image/jpeg')
        else:
            return jsonify({'error': 'Avatar not found'}), 404
    
    try:
        # Decode base64 avatar data
        avatar_binary = base64.b64decode(user.avatar_data)
        mime_type = user.avatar_mimetype or 'image/jpeg'
        return Response(avatar_binary, mimetype=mime_type)
    except Exception as e:
        print(f"Error serving avatar: {e}")
        return jsonify({'error': 'Error loading avatar'}), 500

@app.route('/api/profile/delete', methods=['POST'])
@login_required
def delete_account():
    try:
        # No need to delete files from filesystem since we're not storing them
        # The database cascades will handle deleting chats and files records
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting account: {e}")
        return jsonify({'error': 'Failed to delete account'}), 500

@app.route('/api/chat', methods=['POST'])
@login_required
def save_chat():
    data = request.get_json()
    chat = Chat(user_id=current_user.id, user_message=data.get('user_message', '').strip(), ai_message=data.get('ai_message', '').strip())
    db.session.add(chat)
    db.session.commit()
    return jsonify({
        'message': 'Chat saved',
        'chat_id': chat.id,
        'timestamp': chat.timestamp.isoformat()
    }), 201

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    """Generate AI response using Gemini API"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        file_id = data.get('file_id')
        conversation_id = data.get('conversation_id')  # Optional: to continue existing conversation
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get or create conversation
        conversation = get_or_create_conversation(
            user_id=current_user.id,
            conversation_id=conversation_id,
            first_message=user_message
        )
        
        # Build prompt with file context
        prompt = user_message
        file_context_used = None
        
        if file_id:
            # Specific file provided - use it
            try:
                file_obj = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first()
                if file_obj and file_obj.extracted_text:
                    prompt = f"Context from file \"{file_obj.filename}\":\n{file_obj.extracted_text}\n\nQuestion: {user_message}"
                    file_context_used = file_obj.filename
            except Exception as e:
                print(f"Error loading specific file context: {e}")
        else:
            # No specific file provided - check for active file in conversation or most recent file
            file_obj = None
            
            # First, try to get active file from conversation
            if conversation.active_file_id:
                file_obj = UploadedFile.query.filter_by(
                    id=conversation.active_file_id, 
                    user_id=current_user.id
                ).first()
            
            # If no active file in conversation, get the most recent file for this user
            if not file_obj:
                file_obj = UploadedFile.query.filter_by(
                    user_id=current_user.id
                ).order_by(UploadedFile.uploaded_at.desc()).first()
                
                # If we found a recent file, set it as active for this conversation
                if file_obj:
                    conversation.active_file_id = file_obj.id
            
            # Use the file context if available
            if file_obj and file_obj.extracted_text:
                prompt = f"Context from file \"{file_obj.filename}\":\n{file_obj.extracted_text}\n\nQuestion: {user_message}"
                file_context_used = file_obj.filename
        
        # Get conversation context for better AI responses
        recent_chats = Chat.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Chat.timestamp.desc()).limit(5).all()
        
        if recent_chats:
            context_messages = []
            for chat in reversed(recent_chats):  # Reverse to get chronological order
                context_messages.append(f"User: {chat.user_message}")
                context_messages.append(f"Assistant: {chat.ai_message}")
            
            conversation_context = "\n".join(context_messages)
            prompt = f"Previous conversation:\n{conversation_context}\n\nUser: {user_message}"
        
        # Call Gemini API
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("Error: GEMINI_API_KEY environment variable not set")
            return jsonify({'error': 'AI service not configured'}), 500
        
        # Log API request for debugging (without exposing the full API key)
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"Making Gemini API request with key: {masked_key}")
        print(f"Prompt length: {len(prompt)} characters")
        
        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}',
            headers={'Content-Type': 'application/json'},
            json={
                'contents': [{'parts': [{'text': prompt}]}]
            },
            timeout=30
        )
        
        if not response.ok:
            # Log detailed error information for debugging
            error_details = f"Status: {response.status_code}, Response: {response.text[:500]}"
            print(f"Gemini API Error: {error_details}")
            
            # Return more specific error messages based on status code
            if response.status_code == 400:
                return jsonify({'error': 'Invalid request to AI service. Please try a different message.'}), 400
            elif response.status_code == 401:
                return jsonify({'error': 'AI service authentication failed. Please check API key configuration.'}), 500
            elif response.status_code == 403:
                return jsonify({'error': 'AI service access forbidden. Please check API key permissions.'}), 500
            elif response.status_code == 429:
                return jsonify({'error': 'AI service rate limit exceeded. Please try again in a moment.'}), 429
            elif response.status_code >= 500:
                return jsonify({'error': 'AI service is experiencing issues. Please try again later.'}), 503
            else:
                return jsonify({'error': f'AI service temporarily unavailable (Error {response.status_code})'}), 503
        
        result = response.json()
        ai_response = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
        
        if not ai_response:
            ai_response = 'Sorry, I could not generate a response.'
        
        # Save chat to database
        chat = Chat(
            user_id=current_user.id,
            conversation_id=conversation.id,
            user_message=user_message,
            ai_message=ai_response
        )
        db.session.add(chat)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'response': ai_response,
            'chat_id': chat.id,
            'conversation_id': conversation.id,
            'conversation_title': conversation.title,
            'timestamp': chat.timestamp.isoformat(),
            'file_context_used': file_context_used  # Include which file was used for context
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'AI service timeout. Please try again.'}), 504
    except requests.exceptions.RequestException as e:
        print(f"Gemini API error: {e}")
        return jsonify({'error': 'AI service error. Please try again later.'}), 503
    except Exception as e:
        print(f"Unexpected error in ai_chat: {e}")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for the current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        conversations = Conversation.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(Conversation.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = []
        for conv in conversations.items:
            # Get the latest chat in this conversation
            latest_chat = Chat.query.filter_by(conversation_id=conv.id).order_by(Chat.timestamp.desc()).first()
            # Get total chat count
            chat_count = Chat.query.filter_by(conversation_id=conv.id).count()
            
            result.append({
                'id': conv.id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'chat_count': chat_count,
                'latest_message': latest_chat.user_message[:100] + '...' if latest_chat and len(latest_chat.user_message) > 100 else latest_chat.user_message if latest_chat else None,
                'latest_timestamp': latest_chat.timestamp.isoformat() if latest_chat else None
            })
        
        return jsonify({
            'conversations': result,
            'total': conversations.total,
            'pages': conversations.pages,
            'current_page': conversations.page
        })
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        return jsonify({'error': 'Failed to fetch conversations'}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation_chats(conversation_id):
    """Get all chats in a specific conversation"""
    try:
        # Verify conversation belongs to current user
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        chats = Chat.query.filter_by(conversation_id=conversation_id).order_by(Chat.timestamp.asc()).all()
        
        return jsonify({
            'conversation': {
                'id': conversation.id,
                'title': conversation.title,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat()
            },
            'chats': [{
                'id': chat.id,
                'user_message': chat.user_message,
                'ai_message': chat.ai_message,
                'timestamp': chat.timestamp.isoformat()
            } for chat in chats]
        })
    except Exception as e:
        print(f"Error fetching conversation chats: {e}")
        return jsonify({'error': 'Failed to fetch conversation'}), 500

@app.route('/api/conversations/<int:conversation_id>/title', methods=['PUT'])
@login_required
def update_conversation_title(conversation_id):
    """Update conversation title"""
    try:
        data = request.get_json()
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return jsonify({'error': 'Title is required'}), 400
        
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        conversation.title = new_title[:200]  # Limit title length
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Title updated successfully',
            'title': conversation.title
        })
    except Exception as e:
        print(f"Error updating conversation title: {e}")
        return jsonify({'error': 'Failed to update title'}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete a conversation and all its chats"""
    try:
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Soft delete by marking as inactive
        conversation.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Conversation deleted successfully'})
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return jsonify({'error': 'Failed to delete conversation'}), 500

@app.route('/api/conversations/new', methods=['POST'])
@login_required
def create_new_conversation():
    """Create a new conversation"""
    try:
        data = request.get_json()
        title = data.get('title', 'New Conversation').strip()
        
        conversation = Conversation(
            user_id=current_user.id,
            title=title[:200],  # Limit title length
            is_active=True
        )
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            'message': 'Conversation created successfully',
            'conversation': {
                'id': conversation.id,
                'title': conversation.title,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat(),
                'chat_count': 0
            }
        }), 201
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return jsonify({'error': 'Failed to create conversation'}), 500

@app.route('/api/chats', methods=['GET'])
@login_required
def get_chats():
    """Get chats - now organized by conversations"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        conversation_id = request.args.get('conversation_id', type=int)
        
        if conversation_id:
            # Get chats for specific conversation
            chats = Chat.query.filter_by(
                user_id=current_user.id,
                conversation_id=conversation_id
            ).order_by(Chat.timestamp.asc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        else:
            # Get all chats for user (legacy support)
            chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        return jsonify({
            'chats': [{
                'id': chat.id,
                'conversation_id': chat.conversation_id,
                'user_message': chat.user_message,
                'ai_message': chat.ai_message,
                'timestamp': chat.timestamp.isoformat()
            } for chat in chats.items],
            'total': chats.total,
            'pages': chats.pages,
            'current_page': chats.page
        })
    except Exception as e:
        print(f"Error fetching chats: {e}")
        return jsonify({'error': 'Failed to fetch chats'}), 500

@app.route('/api/chats/<int:chat_id>', methods=['GET'])
@login_required
def get_chat(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    return jsonify({
        'id': chat.id,
        'conversation_id': chat.conversation_id,
        'user_message': chat.user_message,
        'ai_message': chat.ai_message,
        'timestamp': chat.timestamp.isoformat()
    })

@app.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404
    
    conversation_id = chat.conversation_id
    db.session.delete(chat)
    
    # Update conversation timestamp
    conversation = Conversation.query.get(conversation_id)
    if conversation:
        conversation.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'message': 'Chat deleted'}), 200

@app.route('/api/files', methods=['POST'])
@login_required
def upload_file():
    print(f"File upload request received from user: {current_user.username}")
    
    # Check if file is in request
    if 'file' not in request.files:
        print("No file key in request.files")
        return jsonify({'error': 'No file provided in request'}), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        print("Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file is valid
    if not file:
        print("Invalid file object")
        return jsonify({'error': 'Invalid file'}), 400
    
    # Check file extension
    if not allowed_file(file.filename):
        print(f"File type not allowed: {file.filename}")
        return jsonify({'error': f'File type not supported. Allowed types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'}), 400

    try:
        print(f"Starting file processing for: {file.filename}")
        
        # Process file in memory without saving to disk
        filename, file_ext, file_size, extracted_text = process_uploaded_file(file)
        
        print(f"File processed successfully. Text length: {len(extracted_text)}")

        # Save file metadata and extracted text to database
        uploaded_file = UploadedFile(
            user_id=current_user.id,
            filename=filename,
            filetype=file_ext,
            filesize=file_size,
            extracted_text=extracted_text
        )
        db.session.add(uploaded_file)
        db.session.flush()  # Flush to get the file ID
        
        # Set this file as active for the user's most recent conversation
        # or create a new conversation if none exists
        recent_conversation = Conversation.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(Conversation.updated_at.desc()).first()
        
        if recent_conversation:
            # Set this file as active for the most recent conversation
            recent_conversation.active_file_id = uploaded_file.id
            recent_conversation.updated_at = datetime.utcnow()
        else:
            # Create a new conversation with this file as active
            conversation_title = f"Document: {filename}"
            new_conversation = Conversation(
                user_id=current_user.id,
                title=conversation_title,
                active_file_id=uploaded_file.id
            )
            db.session.add(new_conversation)
        
        db.session.commit()
        
        print(f"File saved to database with ID: {uploaded_file.id}")

        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': uploaded_file.id,
            'filename': filename,
            'filetype': file_ext,
            'filesize': file_size,
            'text_length': len(extracted_text),
            'text': extracted_text[:500] + ('...' if len(extracted_text) > 500 else '')  # Return preview
        }), 201
        
    except Exception as e:
        print(f"File upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 500

@app.route('/uploaded-files/<int:file_id>', methods=['GET'])
@login_required
def get_uploaded_file(file_id):
    file = UploadedFile.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not file:
        return jsonify({'error': 'File not found'}), 404
    return jsonify({
        'filename': file.filename,
        'extracted_text': file.extracted_text
    })

@app.route('/api/chats/export', methods=['GET'])
@login_required
def export_chats():
    chats = Chat.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'user_message': c.user_message,
        'ai_message': c.ai_message,
        'timestamp': c.timestamp.isoformat()
    } for c in chats])

@app.route('/api/chats/history', methods=['GET'])
@login_required
def get_chat_history():
    """Get conversation-based chat history for the current user."""
    try:
        # Get conversations instead of individual chats
        limit = min(request.args.get('limit', 20, type=int), 50)  
        offset = request.args.get('offset', 0, type=int)
        
        conversations = Conversation.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(Conversation.updated_at.desc())\
         .offset(offset)\
         .limit(limit)\
         .all()
        
        result = []
        for conv in conversations:
            # Get the latest chat for preview
            latest_chat = Chat.query.filter_by(conversation_id=conv.id).order_by(Chat.timestamp.desc()).first()
            chat_count = Chat.query.filter_by(conversation_id=conv.id).count()
            
            result.append({
                'id': conv.id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'chat_count': chat_count,
                'preview_message': latest_chat.user_message if latest_chat else None,
                'latest_timestamp': latest_chat.timestamp.isoformat() if latest_chat else conv.created_at.isoformat()
            })
        
        total_conversations = Conversation.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        return jsonify({
            'conversations': result,
            'total': total_conversations,
            'limit': limit,
            'offset': offset,
            'user_id': current_user.id
        })
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return jsonify({'error': 'Failed to fetch chat history'}), 500

@app.route('/api/user/stats', methods=['GET'])
@login_required
def get_user_stats():
    """Get statistics for the current user only."""
    try:
        total_chats = Chat.query.filter_by(user_id=current_user.id).count()
        total_files = UploadedFile.query.filter_by(user_id=current_user.id).count()
        
        # Get latest chat
        latest_chat = Chat.query.filter_by(user_id=current_user.id)\
                               .order_by(Chat.timestamp.desc())\
                               .first()
        
        return jsonify({
            'user_id': current_user.id,
            'username': current_user.username,
            'total_chats': total_chats,
            'total_files': total_files,
            'latest_chat_date': latest_chat.timestamp.isoformat() if latest_chat else None,
            'joined_date': current_user.joined_date.isoformat() if current_user.joined_date else None
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user statistics'}), 500

@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html')

@app.route('/test-pdf')
@login_required
def pdf_test_page():
    return render_template('pdf_test.html')

# ========== ERROR HANDLERS ==========
@app.errorhandler(400)
def bad_request(e): return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(401)
def unauthorized(e): return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/conversations/<int:conversation_id>/active-file', methods=['GET'])
@login_required
def get_conversation_active_file(conversation_id):
    """Get the currently active file for a conversation"""
    try:
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        if not conversation.active_file_id:
            return jsonify({
                'active_file': None,
                'message': 'No active file for this conversation'
            })
        
        active_file = UploadedFile.query.filter_by(
            id=conversation.active_file_id,
            user_id=current_user.id
        ).first()
        
        if not active_file:
            # File was deleted but conversation still references it
            conversation.active_file_id = None
            db.session.commit()
            return jsonify({
                'active_file': None,
                'message': 'Active file no longer exists'
            })
        
        return jsonify({
            'active_file': {
                'id': active_file.id,
                'filename': active_file.filename,
                'filetype': active_file.filetype,
                'uploaded_at': active_file.uploaded_at.isoformat(),
                'text_length': len(active_file.extracted_text) if active_file.extracted_text else 0
            }
        })
        
    except Exception as e:
        print(f"Error getting conversation active file: {e}")
        return jsonify({'error': 'Failed to get active file'}), 500

@app.route('/api/conversations/<int:conversation_id>/clear-file', methods=['POST'])
@login_required
def clear_conversation_file(conversation_id):
    """Clear the active file from a conversation"""
    try:
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        conversation.active_file_id = None
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Active file cleared from conversation',
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        print(f"Error clearing conversation file: {e}")
        return jsonify({'error': 'Failed to clear file'}), 500

@app.route('/api/conversations/<int:conversation_id>/set-file', methods=['POST'])
@login_required
def set_conversation_file(conversation_id):
    """Set a specific file as active for a conversation"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400
        
        # Verify the conversation belongs to the user
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=current_user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Verify the file belongs to the user
        file_obj = UploadedFile.query.filter_by(
            id=file_id,
            user_id=current_user.id
        ).first()
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        conversation.active_file_id = file_id
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': f'File "{file_obj.filename}" set as active for conversation',
            'conversation_id': conversation_id,
            'file_id': file_id,
            'filename': file_obj.filename
        })
        
    except Exception as e:
        print(f"Error setting conversation file: {e}")
        return jsonify({'error': 'Failed to set file'}), 500

@app.errorhandler(404)
def not_found(e): return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(413)
def file_too_large(e): return jsonify({'error': 'File too large'}), 413

@app.errorhandler(500)
def server_error(e): return jsonify({'error': 'Internal server error'}), 500

# ========== RUN ==========
with app.app_context():
    db.create_all()

@app.route('/api/files', methods=['GET'])
@login_required
def list_user_files():
    user_files = UploadedFile.query.filter_by(user_id=current_user.id).order_by(UploadedFile.uploaded_at.desc()).all()
    return jsonify([{
        'id': f.id,
        'filename': f.filename,
        'filetype': f.filetype,
        'filesize': f.filesize,
        'uploaded_at': f.uploaded_at.isoformat(),
        'extracted_text': f.extracted_text[:500] + ('...' if len(f.extracted_text) > 500 else '')
    } for f in user_files])

@app.route('/api/test/pdf', methods=['POST'])
@login_required  
def test_pdf_functionality():
    """Test endpoint for PDF functionality debugging"""
    try:
        # Test basic imports
        import PyPDF2
        from PIL import Image
        import pytesseract
        
        response_data = {
            'imports': {
                'PyPDF2': PyPDF2.__version__,
                'PIL': Image.__version__,
                'pytesseract': 'available'
            }
        }
        
        # Test file upload if provided
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                try:
                    filename, file_ext, file_size, extracted_text = process_uploaded_file(file)
                    response_data['file_test'] = {
                        'filename': filename,
                        'file_ext': file_ext,
                        'file_size': file_size,
                        'text_length': len(extracted_text),
                        'text_preview': extracted_text[:200] + ('...' if len(extracted_text) > 200 else ''),
                        'status': 'success'
                    }
                except Exception as e:
                    response_data['file_test'] = {
                        'status': 'error',
                        'error': str(e)
                    }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=os.environ.get('DEBUG', 'false').lower() == 'true')