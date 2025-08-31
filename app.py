#!/usr/bin/env python3
"""
Flask App - NexusChat AI Assistant (MongoDB Version)
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
from flask_cors import CORS
import secrets
from datetime import datetime, timedelta
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
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=int(os.getenv('SESSION_LIFETIME_DAYS', 30)))

# Enable CORS with credentials for frontend-backend on different ports
CORS(app, supports_credentials=True)

# Configure Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-gemini-api-key-here')
print("GEMINI_API_KEY:", repr(GEMINI_API_KEY))
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
vision_model = genai.GenerativeModel('gemini-1.5-flash')

# MongoDB setup
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]

# Allowed file settings
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE_MB', 16)) * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# ========== Homepage Route ==========
# ========== Homepage Route ==========
@app.route("/")
def home():
    # Helper function to format large numbers for display
    def format_stat(num):
        if num >= 1000:
            return f"{num // 1000}K+"
        return str(num)

    try:
        # Get a handle to the required MongoDB collections
        chat_sessions_collection = get_collection("chat_sessions")
        uploaded_items_collection = get_collection("uploaded_items")

        # Count the total number of documents in each collection
        total_conversations = chat_sessions_collection.count_documents({})
        total_files = uploaded_items_collection.count_documents({})

        # Prepare a dictionary with the formatted stats
        stats = {
            "conversations": format_stat(total_conversations),
            "files_analyzed": format_stat(total_files),
            "uptime": "99.9%"  # Uptime is best kept as a static value here
        }
    except Exception as e:
        # In case of a database error, log it and fall back to default values
        print(f"Could not fetch stats from the database: {e}")
        stats = {
            "conversations": "10K+",
            "files_analyzed": "5K+",
            "uptime": "99.9%"
        }

    # Render the homepage template, passing the 'stats' dictionary to it
    return render_template("index.html", stats=stats)

# ========== Web Page Routes ==========
@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/profile")
def profile_page():
    return render_template("profile.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")


def get_collection(name):
    return mongo_db[name]


# ========== Utility Functions ==========

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_delete_temp_file(file_path):
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception:
        pass


def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = "".join([page.get_text() for page in doc])
        doc.close()
        return text.strip()
    except Exception:
        return ""


def extract_text_from_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        image.close()
        return text.strip()
    except Exception:
        return ""


def analyze_image_with_vision(file_path, user_prompt="Describe this image"):
    try:
        image = Image.open(file_path)
        if image.mode != "RGB":
            image = image.convert("RGB")
        response = vision_model.generate_content([user_prompt, image])
        image.close()
        return {"success": True, "analysis": response.text}
    except Exception as e:
        return {"success": False, "analysis": f"Error: {str(e)}"}


def get_ai_response(prompt, context=""):
    try:
        system_prompt = """You are NexusChat, a friendly AI assistant."""
        full_prompt = f"{system_prompt}\n\nContext: {context}\n\nUser: {prompt}\nAssistant:"
        response = model.generate_content(full_prompt)
        return response.text if response.text else "No response."
    except Exception as e:
        return f"AI error: {str(e)}"


# ========== Authentication Decorator ==========
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated


# ========== Auth Routes (MongoDB) ==========

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    users = get_collection("users")
    if users.find_one({"$or": [{"username": username}, {"email": email}]}):
        return jsonify({"error": "User already exists"}), 400

    password_hash = generate_password_hash(password)
    user_doc = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "date_created": datetime.utcnow(),
        "theme": "light",
        "language": "en",
        "notifications": True
    }
    result = users.insert_one(user_doc)
    session["user_id"] = str(result.inserted_id)
    session["username"] = username
    return jsonify({"message": "Signup successful"}), 200


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    users = get_collection("users")
    user = users.find_one({"username": username})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = str(user["_id"])
    session["username"] = user["username"]
    return jsonify({"message": "Login successful"}), 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# ========== Profile Routes ==========

@app.route("/api/profile", methods=["GET"])
@login_required
def get_profile():
    users = get_collection("users")
    user = users.find_one({"_id": ObjectId(session["user_id"])})
    return jsonify({
        "username": user["username"],
        "email": user["email"],
        "theme": user.get("theme", "light"),
        "language": user.get("language", "en"),
        "notifications": user.get("notifications", True),
        "joined": user.get("date_created").strftime("%Y-%m-%d")
    })


@app.route("/api/profile/update", methods=["POST"])
@login_required
def update_profile():
    data = request.get_json()
    users = get_collection("users")
    update_data = {k: v for k, v in data.items() if k in ["email", "username", "theme", "language", "notifications"]}
    password_changed = False
    if "password" in data and data["password"]:
        update_data["password_hash"] = generate_password_hash(data["password"])
        password_changed = True
    users.update_one({"_id": ObjectId(session["user_id"])} , {"$set": update_data})
    if password_changed:
        return jsonify({"message": "Password updated successfully"})
    return jsonify({"message": "Profile updated"})


# ========== Export & Search Chat History ========== 

@app.route("/api/chats/export", methods=["GET"])
@login_required
def export_chat_history():
    messages = get_collection("messages")
    chat_sessions = get_collection("chat_sessions")
    user_sessions = list(chat_sessions.find({"user_id": session["user_id"]}))
    session_ids = [str(s["_id"]) for s in user_sessions]
    all_messages = list(messages.find({"session_id": {"$in": session_ids}}).sort("timestamp", 1))
    # Convert ObjectId and datetime to string
    for m in all_messages:
        m["_id"] = str(m["_id"])
        m["timestamp"] = m["timestamp"].isoformat() if m.get("timestamp") else ""
    return jsonify(all_messages), 200

@app.route("/api/chats/search", methods=["GET"])
@login_required
def search_chat_history():
    query = request.args.get("q", "").strip().lower()
    messages = get_collection("messages")
    chat_sessions = get_collection("chat_sessions")
    user_sessions = list(chat_sessions.find({"user_id": session["user_id"]}))
    session_ids = [str(s["_id"]) for s in user_sessions]
    results = []
    if query:
        found = messages.find({
            "session_id": {"$in": session_ids},
            "content": {"$regex": query, "$options": "i"}
        }).sort("timestamp", -1)
        for m in found:
            results.append({
                "session_id": m["session_id"],
                "content": m["content"],
                "timestamp": m["timestamp"].isoformat() if m.get("timestamp") else "",
                "sender": m.get("sender", "user"),
                "session_name": m.get("session_id", "")
            })
    return jsonify({"results": results}), 200

# ========== Chat Sessions & Messages ==========

# Endpoint to fetch all messages for a session (for chat history)
@app.route("/api/session/<session_id>", methods=["GET"])
@login_required
def get_session_messages(session_id):
    messages = get_collection("messages")
    msgs = list(messages.find({"session_id": session_id}).sort("timestamp", 1))
    result = []
    for m in msgs:
        result.append({
            "sender": m.get("sender"),
            "content": m.get("content"),
            "timestamp": m.get("timestamp").isoformat() if m.get("timestamp") else ""
        })
    return jsonify({"messages": result}), 200

# GET endpoint to fetch all chat sessions for the logged-in user
@app.route("/api/sessions", methods=["GET"])
@login_required
def get_sessions():
    sessions = get_collection("chat_sessions")
    user_sessions = list(sessions.find({"user_id": session["user_id"]}).sort("updated_at", -1))
    result = []
    messages = get_collection("messages")
    for s in user_sessions:
        # Get the first user message for this session (for title)
        first_user_msg = messages.find_one({"session_id": str(s["_id"]), "sender": "user"}, sort=[("timestamp", 1)])
        last_user_msg = messages.find_one({"session_id": str(s["_id"]), "sender": "user"}, sort=[("timestamp", -1)])
        result.append({
            "id": str(s["_id"]),
            "first_message": first_user_msg["content"] if first_user_msg else "",
            "created_at": s.get("created_at").strftime("%Y-%m-%d %H:%M:%S") if s.get("created_at") else None,
            "updated_at": s.get("updated_at").strftime("%Y-%m-%d %H:%M:%S") if s.get("updated_at") else None,
            "user_message": last_user_msg["content"] if last_user_msg else "",
            "timestamp": last_user_msg["timestamp"].isoformat() if last_user_msg and last_user_msg.get("timestamp") else s.get("updated_at").isoformat() if s.get("updated_at") else ""
        })
    return jsonify({"sessions": result}), 200

@app.route("/api/sessions", methods=["POST"])
@app.route("/api/new_session", methods=["POST"])
@login_required
def create_session():
    try:
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        sessions = get_collection("chat_sessions")
        new_session = {
            "user_id": session["user_id"],
            "session_name": "New Chat",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = sessions.insert_one(new_session)
        return jsonify({"session_id": str(result.inserted_id)})
    except Exception as e:
        return jsonify({"error": f"Session creation failed: {str(e)}"}), 500


@app.route("/api/message", methods=["POST"])
@login_required
def send_message():
    data = request.get_json()
    session_id = data.get("session_id")
    content = data.get("content", "").strip()

    messages = get_collection("messages")
    chat_sessions = get_collection("chat_sessions")

    # Save user message
    messages.insert_one({
        "session_id": session_id,
        "sender": "user",
        "content": content,
        "timestamp": datetime.utcnow()
    })

    # Gather file context if any files are uploaded for this session
    uploaded_items = get_collection("uploaded_items")
    analysis_results = get_collection("analysis_results")
    file_docs = list(uploaded_items.find({"session_id": session_id}))
    file_contexts = []
    for file_doc in file_docs:
        if file_doc.get("extracted_text"):
            file_contexts.append(f"Extracted text from {file_doc.get('original_filename','file')}:\n{file_doc['extracted_text'][:2000]}")
    # Add vision analysis if available
    for file_doc in file_docs:
        vision = analysis_results.find_one({"item_id": str(file_doc["_id"]), "analysis_type": "vision_analysis"})
        if vision and vision.get("summary"):
            file_contexts.append(f"Vision analysis for {file_doc.get('original_filename','file')}:\n{vision['summary'][:1000]}")

    # Compose context for Gemini
    if file_contexts:
        file_context = "\n\n".join(file_contexts)
        prompt = (
            f"You are an expert assistant. Answer the user's question based ONLY on the following uploaded document(s) or image(s).\n"
            f"User question: {content}\n"
            f"\n---\n\n{file_context}\n\nIf the answer is not in the document/image, say 'I could not find the answer in the uploaded file.'"
        )
        ai_reply = get_ai_response(prompt)
    else:
        # Fallback: use recent chat context
        recent_msgs = list(messages.find({"session_id": session_id}).sort("timestamp", -1).limit(5))
        context = "\n".join([f"{m['sender']}: {m['content']}" for m in reversed(recent_msgs)])
        ai_reply = get_ai_response(content, context)

    messages.insert_one({
        "session_id": session_id,
        "sender": "assistant",
        "content": ai_reply,
        "timestamp": datetime.utcnow()
    })

    chat_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"updated_at": datetime.utcnow()}})

    return jsonify({"user_message": content, "ai_message": ai_reply})


# ========== File Upload & Analysis (MongoDB) ==========
# ========== File Upload & Analysis (MongoDB) ==========

@app.route("/api/upload", methods=["POST"])
@login_required
def upload_file():
    """Upload and analyze a file (MongoDB)"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    session_id = request.form.get("session_id")

    if not session_id:
        return jsonify({"error": "Session ID required"}), 400
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    chat_sessions = get_collection("chat_sessions")
    uploaded_items = get_collection("uploaded_items")
    analysis_results = get_collection("analysis_results")

    # Verify session belongs to user
    sess = chat_sessions.find_one({"_id": ObjectId(session_id), "user_id": session["user_id"]})
    if not sess:
        return jsonify({"error": "Session not found"}), 404

    # Read file into memory
    file.seek(0)
    file_content = file.read()
    file_size = len(file_content)
    mime_type = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    # Extract text / analyze
    original_filename = secure_filename(file.filename)
    file_ext = original_filename.rsplit(".", 1)[1].lower()
    extracted_text = ""
    vision_analysis = None
    file_type = "other"

    temp_file = None
    try:
        if file_ext == "pdf":
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_file.write(file_content)
            temp_file.close()
            extracted_text = extract_text_from_pdf(temp_file.name)
            file_type = "pdf"
        elif file_ext in ["png", "jpg", "jpeg", "gif", "webp"]:
            temp_file = tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False)
            temp_file.write(file_content)
            temp_file.close()
            extracted_text = extract_text_from_image(temp_file.name)
            vision_analysis = analyze_image_with_vision(temp_file.name)
            file_type = "image"
    finally:
        if temp_file:
            safe_delete_temp_file(temp_file.name)

    # Save file metadata in DB
    item_doc = {
        "session_id": session_id,
        "user_id": session["user_id"],
        "original_filename": original_filename,
        "file_type": file_type,
        "file_size": file_size,
        "mime_type": mime_type,
        "file_content": file_content,
        "extracted_text": extracted_text,
        "uploaded_at": datetime.utcnow(),
    }
    item_result = uploaded_items.insert_one(item_doc)
    item_id = str(item_result.inserted_id)

    # Save analyses
    analyses = []
    if extracted_text.strip():
        text_summary = get_ai_response(
            f"Summarize and extract key points:\n\n{extracted_text[:2000]}"
        )
        analysis_results.insert_one({
            "item_id": item_id,
            "session_id": session_id,
            "analysis_type": f"{file_type}_text_analysis",
            "summary": text_summary,
            "created_at": datetime.utcnow(),
        })
        analyses.append({"type": "text_analysis", "content": text_summary})

    if file_type == "image" and vision_analysis:
        analysis_results.insert_one({
            "item_id": item_id,
            "session_id": session_id,
            "analysis_type": "vision_analysis",
            "summary": vision_analysis["analysis"],
            "created_at": datetime.utcnow(),
        })
        analyses.append({
            "type": "vision_analysis",
            "content": vision_analysis["analysis"],
            "success": vision_analysis["success"],
        })

    # Update session timestamp
    chat_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"updated_at": datetime.utcnow()}}
    )

    response_data = {
        "message": "File uploaded and analyzed successfully",
        "file_id": item_id,
        "filename": original_filename,
        "file_type": file_type,
        "analyses": analyses,
        "analysis_available": len(analyses) > 0,
    }
    if extracted_text.strip():
        response_data["extracted_text"] = (
            extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
        )
    if file_type == "image" and vision_analysis and vision_analysis["success"]:
        response_data["vision_preview"] = (
            vision_analysis["analysis"][:300] + "..."
            if len(vision_analysis["analysis"]) > 300
            else vision_analysis["analysis"]
        )

    return jsonify(response_data), 200


@app.route("/api/analyses/<session_id>", methods=["GET"])
@login_required
def get_analyses(session_id):
    """Get all file analyses for a session"""
    analysis_results = get_collection("analysis_results")
    uploaded_items = get_collection("uploaded_items")

    analyses = list(analysis_results.find({"session_id": session_id}).sort("created_at", -1))
    result = []
    for analysis in analyses:
        item = uploaded_items.find_one({"_id": ObjectId(analysis["item_id"])})
        result.append({
            "id": str(analysis["_id"]),
            "item_id": str(analysis["item_id"]),
            "analysis_type": analysis.get("analysis_type"),
            "summary": analysis.get("summary"),
            "created_at": analysis.get("created_at").strftime("%Y-%m-%d %H:%M:%S"),
            "filename": item["original_filename"] if item else "",
            "file_type": item["file_type"] if item else "",
        })
    return jsonify({"analyses": result}), 200


@app.route("/api/delete_item/<item_id>", methods=["DELETE"])
@login_required
def delete_uploaded_item(item_id):
    """Delete an uploaded item and its analyses"""
    uploaded_items = get_collection("uploaded_items")
    analysis_results = get_collection("analysis_results")

    item = uploaded_items.find_one({"_id": ObjectId(item_id)})
    if not item or item["user_id"] != session["user_id"]:
        return jsonify({"error": "Item not found"}), 404

    analysis_results.delete_many({"item_id": item_id})
    uploaded_items.delete_one({"_id": ObjectId(item_id)})

    return jsonify({"message": "Item deleted successfully"}), 200
# ==================== INIT ====================
if __name__ == "__main__":
    try:
        mongo_db.list_collection_names()
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        exit(1)

    # Use environment variables for host/port if set (Render sets PORT)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Production static file serving for Render (when using gunicorn)
if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    from whitenoise import WhiteNoise
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(os.path.dirname(__file__), 'static'))
