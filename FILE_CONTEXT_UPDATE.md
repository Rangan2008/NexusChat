# 📄 File Context Management Update

## Overview
Updated the Nexus Chatbot to automatically use the most recently uploaded file as context for AI conversations. When a user uploads a new PDF or document, the AI will automatically reference that file instead of previous uploads.

## 🔧 Changes Made

### 1. Database Schema Updates
- **Added `active_file_id` column** to the `Conversation` model
- **Added `active_file` relationship** to link conversations with their active files
- **Migration script** (`migrate_db.py`) created to update existing databases

### 2. Enhanced File Upload Logic
When a user uploads a file:
- The file is automatically set as the **active file** for the user's most recent conversation
- If no recent conversation exists, a **new conversation is created** with the uploaded file as active
- The conversation title includes the document name for easy identification

### 3. Improved AI Chat Logic
The AI chat now follows this priority order for file context:
1. **Specific file_id provided** → Use that exact file
2. **Active file in current conversation** → Use the conversation's active file
3. **Most recent user upload** → Use the user's latest uploaded file
4. **No file context** → Chat normally without document context

### 4. New API Endpoints
- `GET /api/conversations/<id>/active-file` - Get the active file for a conversation
- `POST /api/conversations/<id>/clear-file` - Remove active file from conversation
- `POST /api/conversations/<id>/set-file` - Set a specific file as active

### 5. Enhanced Response Data
AI chat responses now include:
- `file_context_used` - Name of the file used for context (if any)
- Users can see which document the AI is referencing

## 🚀 How It Works

### File Upload Flow
1. User uploads a PDF/image → Text extracted
2. File becomes active for most recent conversation
3. Future questions automatically reference this file

### Chat Flow
1. User asks a question
2. System checks for active file in conversation
3. If found, includes file content as context
4. AI responds based on document content
5. Response indicates which file was used

### Multiple Files
- **New upload** → Replaces previous as active file
- **Switch files** → Use API endpoints to change active file
- **Clear context** → Remove file context from conversation

## 🛠️ API Usage Examples

### Get Active File for Conversation
```javascript
GET /api/conversations/123/active-file
// Response: { "active_file": { "id": 456, "filename": "document.pdf", ... }}
```

### Clear Active File
```javascript
POST /api/conversations/123/clear-file
// Response: { "message": "Active file cleared from conversation" }
```

### Set Specific File as Active
```javascript
POST /api/conversations/123/set-file
// Body: { "file_id": 789 }
// Response: { "message": "File \"report.pdf\" set as active for conversation" }
```

## 🎯 User Experience
- **Seamless**: Upload a file → Ask questions → AI automatically uses latest file
- **Transparent**: AI responses show which document is being referenced
- **Flexible**: Can switch between files or clear context as needed
- **Organized**: Document-based conversations are clearly labeled

## 🔄 Migration Required
For existing installations:
1. Run the migration script: `python migrate_db.py`
2. This adds the `active_file_id` column to existing databases
3. No data loss - existing conversations remain intact

## 📋 Testing Checklist
- [ ] Upload a PDF → Verify it becomes active
- [ ] Ask questions → Verify AI uses the PDF context
- [ ] Upload another PDF → Verify it replaces the first as active
- [ ] Use API endpoints to clear/set active files
- [ ] Check response includes `file_context_used`
- [ ] Verify conversation titles show document names

This update ensures users always get relevant responses based on their most recent document upload, making the chatbot much more intuitive for document-based conversations.
