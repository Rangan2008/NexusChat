# 🤖 NexusChat - AI-Powered Chat Application

A modern, full-featured Flask-based chat application with advanced AI integration, comprehensive file analysis, and intelligent image recognition capabilities.

![NexusChat](https://img.shields.io/badge/Python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![AI](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Key Features

### 🧠 Advanced AI Integration
- **Google Gemini AI**: Powered by cutting-edge language models
- **Context-Aware Conversations**: Maintains conversation history and context
- **Intelligent Responses**: Natural, human-like interactions

### 🖼️ Complete Image Analysis
- **Visual Recognition**: Describes scenes, objects, and visual content
- **OCR Text Extraction**: Extracts text from images using Tesseract
- **Custom Analysis**: Ask specific questions about uploaded images
- **Dual Processing**: Combines both visual AI and OCR capabilities

### 📄 Document Processing
- **PDF Analysis**: Extract and analyze text from PDF documents
- **Multi-format Support**: Handle various file types seamlessly
- **AI Summarization**: Automatic content analysis and key points extraction

### 👤 User Management
- **Secure Authentication**: Registration, login with password hashing
- **Session Management**: Persistent login sessions
- **User Profiles**: Customizable user profiles and preferences

### 💬 Chat Features
- **Multiple Sessions**: Organize conversations in separate sessions
- **File Integration**: Chat about uploaded files and images
- **Real-time Interface**: Modern, responsive chat interface
- **Message History**: Complete conversation persistence

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MySQL database
- Google Gemini API key
- Tesseract OCR (for image text extraction)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/nexuschat.git
   cd nexuschat
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Initialize database**
   ```bash
   python setup_mysql.py
   ```

6. **Run the application**
   ```bash
   python app_mysql.py
   ```

Visit `http://localhost:5000` to start using NexusChat!

## 🔧 Configuration

### Environment Variables
Create a `.env` file with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-super-secret-key
FLASK_ENV=development
DEBUG=True

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# MySQL Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=your-username
DB_PASSWORD=your-password
DB_NAME=chatbot

# File Upload
MAX_FILE_SIZE_MB=16
SESSION_LIFETIME_DAYS=30
```

### Database Setup
The application uses MySQL for data persistence:
- User authentication and profiles
- Chat sessions and messages
- File metadata and content
- AI analysis results

## 📱 Usage

### Basic Chat
1. Register an account or login
2. Start a new chat session
3. Begin conversing with the AI

### Image Analysis
1. Upload an image using the 📎 button
2. Get automatic visual analysis and OCR results
3. Click "🔍 Analyze" for custom image questions
4. Ask follow-up questions about the image

### Document Processing
1. Upload PDF files
2. Get automatic text extraction and analysis
3. Ask questions about document content
4. Receive AI-powered summaries and insights

## 🏗️ Architecture

### Backend
- **Flask**: Web application framework
- **MySQL**: Primary database for persistence
- **Google Gemini**: AI language and vision models
- **PyMuPDF**: PDF text extraction
- **Pytesseract**: OCR for image text extraction
- **Pillow**: Image processing

### Frontend
- **Modern HTML5/CSS3**: Responsive design
- **Vanilla JavaScript**: Interactive features
- **CSS Grid/Flexbox**: Responsive layouts
- **CSS Variables**: Theme customization

### Database Schema
- `users`: User accounts and profiles
- `chat_sessions`: Conversation sessions
- `messages`: Chat messages and AI responses
- `uploaded_items`: File metadata and content
- `analysis_results`: AI analysis data

## 🔐 Security Features

- **Password Hashing**: Werkzeug security for password protection
- **Session Management**: Secure session handling
- **File Validation**: Safe file upload with type checking
- **Environment Variables**: Sensitive data protection
- **SQL Injection Protection**: Parameterized queries

## 🌐 Deployment

### Quick Deploy Options
- **Railway**: One-click deployment with database
- **Heroku**: Classic platform with add-ons
- **Render**: Modern deployment platform
- **DigitalOcean**: VPS deployment for full control

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## 📊 API Endpoints

### Authentication
- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login  
- `POST /api/auth/logout` - User logout

### Chat Management
- `POST /api/new_session` - Create new chat session
- `GET /api/sessions` - List user sessions
- `GET /api/session/<id>` - Load specific session
- `POST /api/message` - Send message to AI

### File Operations
- `POST /api/upload` - Upload and analyze files
- `POST /api/analyze_image/<id>` - Custom image analysis
- `GET /api/analyses/<session_id>` - Get analysis results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini AI** for advanced language and vision capabilities
- **Flask Community** for the excellent web framework
- **Tesseract OCR** for optical character recognition
- **Open Source Community** for the amazing tools and libraries

## 📞 Support

If you encounter any issues or have questions:
1. Check the [Issues](https://github.com/yourusername/nexuschat/issues) page
2. Read the [DEPLOYMENT.md](DEPLOYMENT.md) guide
3. Create a new issue if needed

---

**Built with ❤️ using Flask, Google Gemini AI, and modern web technologies**
- **Delete session** (`/api/delete_session/<session_id>`): Complete session removal
- **Delete uploaded item** (`/api/delete_item/<item_id>`): File cleanup
- **User profile** (`/api/profile`): Profile management and statistics
- **Update profile** (`/api/profile/update`): Account modification
- User analytics and usage statistics

## 📋 Requirements

### System Dependencies
- Python 3.8+
- Tesseract OCR
  - Windows: [Download installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Linux: `apt-get install tesseract-ocr`

### Python Packages
Install via `pip install -r requirements.txt`:

- Flask 3.0.0
- Werkzeug 3.0.1
- google-generativeai 0.3.2
- PyMuPDF 1.23.8 (PDF processing)
- Pillow 10.1.0 (Image processing)
- pytesseract 0.3.10 (OCR)
- bcrypt 4.1.2 (Password hashing)
- python-dotenv 1.0.0 (Environment variables)

## 🛠️ Installation

### 1. Clone and Setup
```bash
cd "d:\Programming\web dev\Ai chatbot"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env with your configuration:
# - Set SECRET_KEY for session security
# - Add your GEMINI_API_KEY from Google AI Studio
# - Configure other settings as needed
```

### 4. Run Setup Script
```bash
python setup.py
```

### 5. Start the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🔧 Configuration

### Environment Variables (.env)
```env
SECRET_KEY=your-super-secret-key-change-this
GEMINI_API_KEY=your-gemini-api-key-here
FLASK_ENV=development
DEBUG=True
DATABASE_URL=sqlite:///nexuschat.db
UPLOAD_FOLDER=uploads
MAX_FILE_SIZE_MB=16
SESSION_LIFETIME_DAYS=30
```

### Getting a Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file

## 📂 Project Structure

```
Ai chatbot/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── setup.py              # Setup and initialization script
├── .env.example          # Environment configuration template
├── nexuschat.db          # SQLite database (created automatically)
├── uploads/              # File upload directory
├── static/               # Static assets (CSS, JS, images)
│   ├── script.js         # Frontend JavaScript
│   └── public/           # CSS files
│       ├── style.css
│       ├── chat.css
│       └── profile.css
└── templates/            # HTML templates
    ├── index.html        # Landing page
    ├── login.html        # Login page
    ├── signup.html       # Registration page
    ├── chat.html         # Main chat interface
    └── profile.html      # User profile page
```

## 🗄️ Database Schema

### Tables
- **users**: User accounts and preferences
- **chat_sessions**: Individual chat sessions
- **messages**: Conversation messages
- **uploaded_items**: File upload metadata
- **analysis_results**: AI analysis of uploaded files

### Relationships
- Users have many chat sessions
- Sessions contain many messages and uploaded items
- Uploaded items have associated analysis results
- All data properly cascades on user/session deletion

## 🔐 Security Features

- **Password Hashing**: Werkzeug PBKDF2 hashing
- **Session Management**: Secure Flask sessions
- **File Upload Security**: Extension validation, secure naming
- **User Isolation**: Session-based access control
- **SQL Injection Protection**: Parameterized queries
- **CSRF Protection**: Built-in Flask security

## 🌐 API Endpoints

### Authentication
- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

### Sessions
- `GET /api/sessions` - List user sessions
- `POST /api/new_session` - Create new session
- `GET /api/session/<id>` - Get session details
- `DELETE /api/delete_session/<id>` - Delete session

### Messaging
- `POST /api/message` - Send message
- `GET /api/messages/<session_id>` - Get messages

### File Operations
- `POST /api/upload` - Upload file
- `GET /api/analyses/<session_id>` - Get analyses
- `POST /api/ask_about_file` - Question about file
- `DELETE /api/delete_item/<id>` - Delete file

### Profile
- `GET /api/profile` - Get user profile
- `POST /api/profile/update` - Update profile

## 🚀 Usage Examples

### Starting a Chat Session
```javascript
// Create new session
const response = await fetch('/api/new_session', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'My Chat' })
});
const { session_id } = await response.json();

// Send a message
await fetch('/api/message', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_id: session_id,
        content: 'Hello, AI!'
    })
});
```

### Uploading and Analyzing a File
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('session_id', currentSessionId);

const response = await fetch('/api/upload', {
    method: 'POST',
    credentials: 'include',
    body: formData
});

const result = await response.json();
console.log('Analysis:', result.analysis_available);
```

## 🔍 Troubleshooting

### Common Issues

1. **Import errors for fitz/pytesseract**
   - Install: `pip install PyMuPDF pytesseract`
   - Ensure Tesseract is in system PATH

2. **Database errors**
   - Run: `python setup.py` to initialize
   - Check file permissions in project directory

3. **File upload failures**
   - Verify uploads/ directory exists and is writable
   - Check file size limits (16MB default)

4. **AI responses not working**
   - Verify GEMINI_API_KEY in .env file
   - Check API key validity and quota

### Development Mode
```bash
export FLASK_ENV=development
export DEBUG=True
python app.py
```

## 📚 Additional Features

### Theme Support
- Light/Dark theme switching
- User preference persistence
- CSS custom properties for theming

### Mobile Responsive
- Adaptive UI for mobile devices
- Touch-friendly interface
- Progressive Web App features

### File Format Support
- **PDFs**: Full text extraction and analysis
- **Images**: OCR text recognition (PNG, JPG, JPEG, GIF, WEBP)
- **Text files**: Direct content analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the setup.py output for configuration issues
3. Ensure all dependencies are properly installed
4. Verify environment configuration

---

**NexusChat** - Where AI meets conversation! 🤖✨
