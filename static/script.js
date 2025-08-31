// ✅ Enhanced NexusChat with organized chat history and user features

class NexusChat {
  constructor() {
    this.activeFileId = null;
    this.isTyping = false;
    this.currentUser = null;
    this.activeChatId = null;
    this.activeConversationId = null; // Track current conversation
    this.conversations = []; // Store conversations
    this.initElements();
    this.initEventListeners();
    this.initializeUser();
    this.loadConversations();
  }

  initElements() {
    this.elements = {
      userInput: document.getElementById('user-input'),
      messages: document.getElementById('messages'),
      typingIndicator: document.getElementById('typing-indicator'),
      sendBtn: document.getElementById('send-btn'),
      voiceBtn: document.getElementById('voice-btn'),
      fileInput: document.getElementById('file-upload'),
      uploadBtn: document.getElementById('upload-btn'),
      activeFileIndicator: document.getElementById('active-file-indicator'),
      chatHistoryContainer: document.getElementById('chat-history-container'),
      newChatBtn: document.getElementById('new-chat-btn'),
      exportChatBtn: document.getElementById('export-chat-btn'),
      filePreview: document.getElementById('file-preview'),
      fileUploadSection: document.getElementById('file-upload-section'),
      userAvatar: document.getElementById('desktop-user-avatar'), // ✅ Not user-avatar!
      userInfo: document.getElementById('user-info')
    };
  }

  initEventListeners() {
    // Desktop user avatar dropdown
    const desktopAvatar = document.getElementById('desktop-user-avatar');
    const desktopDropdown = document.getElementById('user-dropdown-menu');

    desktopAvatar?.addEventListener('click', (e) => {
      e.stopPropagation();
      desktopDropdown.classList.toggle('show');
    });

    document.addEventListener('click', () => {
      desktopDropdown.classList.remove('show');
    });

    desktopDropdown?.addEventListener('click', (e) => e.stopPropagation());
    // Profile
    document.getElementById('profile-btn').addEventListener('click', () => {
      window.location.href = '/profile';
    });

    // Theme Toggle
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      document.getElementById('user-dropdown-menu').classList.remove('show');
    });

    // Logout
    document.getElementById('logout-dropdown')?.addEventListener('click', async () => {
      try {
        const response = await fetch('/api/auth/logout', {
          method: 'POST',
          credentials: 'include'
        });
        if (response.ok) {
          window.location.href = '/login';
        }
      } catch (error) {
        console.error('Logout error:', error);
      }
    });

    this.elements.userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    this.elements.sendBtn?.addEventListener('click', () => this.sendMessage());
    this.elements.voiceBtn?.addEventListener('click', () => this.startVoiceRecognition());

    // Support multiple file/folder upload
    this.elements.fileInput?.addEventListener('change', (e) => {
      const files = Array.from(e.target.files);
      if (!files.length) return;
      this.uploadMultipleFiles(files);
    });

    this.elements.uploadBtn?.addEventListener('click', () => this.handleFileUpload());
    this.elements.newChatBtn?.addEventListener('click', () => this.createNewConversation());
    this.elements.exportChatBtn?.addEventListener('click', () => this.exportChatHistory());
  }

  async initializeUser() {
    try {
      const response = await fetch('/api/profile', { credentials: 'include' });
      if (response.ok) {
        const userData = await response.json();
        this.currentUser = userData;
        this.updateUserInterface(userData);
      } else if (response.status === 401) {
        window.location.href = '/login';
      }
    } catch (error) {
      console.error('Failed to load user data:', error);
    }
  }

  updateUserInterface(userData) {
    if (userData && userData.username) {
      // Update desktop avatar (which now appears on mobile too)
      const desktopAvatar = document.getElementById('desktop-user-avatar');
      
      if (userData.avatar && userData.avatar !== '/static/Avatar.jpeg') {
        // User has custom avatar
        desktopAvatar.innerHTML = `<img src="${userData.avatar}" alt="User Avatar" class="avatar-image">`;
      } else {
        // Use initials
        const initials = userData.username.substring(0, 2).toUpperCase();
        desktopAvatar.innerHTML = `<span class="avatar-initials">${initials}</span>`;
      }

      // Update user info in header
      if (this.elements.userInfo) {
        this.elements.userInfo.textContent = `Welcome, ${userData.username}`;
      }
    }
  }

  // Legacy method - redirects to new conversation system
  async loadChatHistory() {
    await this.loadConversations();
  }

  organizeAndDisplayChatHistory(chats) {
    if (!chats || chats.length === 0) {
      this.elements.chatHistoryContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; margin: 1rem 0;">No chat history yet.</p>';
      return;
    }

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const groups = {
      today: [],
      yesterday: [],
      past7days: [],
      older: []
    };

    chats.forEach(chat => {
      const chatDate = new Date(chat.timestamp);
      const chatDay = new Date(chatDate.getFullYear(), chatDate.getMonth(), chatDate.getDate());

      if (chatDay.getTime() === today.getTime()) {
        groups.today.push(chat);
      } else if (chatDay.getTime() === yesterday.getTime()) {
        groups.yesterday.push(chat);
      } else if (chatDay >= sevenDaysAgo) {
        groups.past7days.push(chat);
      } else {
        groups.older.push(chat);
      }
    });

    let historyHTML = '';

    const groupLabels = {
      today: 'Today',
      yesterday: 'Yesterday',
      past7days: 'Past 7 Days',
      older: 'Older'
    };

    Object.entries(groups).forEach(([groupKey, groupChats]) => {
      if (groupChats.length > 0) {
        historyHTML += `
          <div class="history-group">
            <div class="history-group-title">${groupLabels[groupKey]}</div>
            ${groupChats.map(chat => `
              <div class="chat-history-item ${this.activeChatId === chat.id ? 'active' : ''}" 
                   data-chat-id="${chat.id}" 
                                      onclick="window.nexusChat.loadSpecificChat('${chat.id}')"&gt;
                <h4>${this.truncateMessage(chat.user_message || 'No message', 50)}</h4>
                <p>${this.formatChatTime(chat.timestamp)}</p>
              </div>
            `).join('')}
          </div>
        `;
      }
    });

    this.elements.chatHistoryContainer.innerHTML = historyHTML;
  }

  truncateMessage(message, maxLength) {
    if (message.length <= maxLength) return message;
    return message.substring(0, maxLength) + '...';
  }

  formatChatTime(timestamp) {
  const date = new Date(timestamp);
  // Always show full date and time in a readable format
  return date.toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  async sendMessage(text) {
    if (this.isTyping) return;
    const inputText = text || this.elements.userInput.value.trim();
    if (!inputText) return;

    this.elements.userInput.value = '';
    this.elements.userInput.style.height = 'auto';

    // Clear empty state
    const emptyState = this.elements.messages.querySelector('.empty-state');
    if (emptyState) {
      emptyState.remove();
    }

    this.renderMessage(inputText, 'user');

    try {
      this.isTyping = true;
      this.showTypingIndicator(true);
      const aiResponse = await this.getAIResponse(inputText);
      this.showTypingIndicator(false);
      this.renderMessage(aiResponse, 'ai');
      // Chat is already saved in getAIResponse, so refresh conversations
      await this.loadConversations();
    } catch (error) {
      console.error('Error in sendMessage:', error);
      this.showTypingIndicator(false);
      this.renderMessage(`Error: ${error.message}`, 'ai');
    } finally {
      this.isTyping = false;
      this.scrollToBottom();
    }
  }

  async loadConversations() {
    try {
      const response = await fetch('/api/sessions', {
        method: 'GET',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to fetch sessions');
      }

      const data = await response.json();
      this.conversations = data.sessions || [];
      this.displayConversationHistory(data.sessions || []);
    } catch (error) {
      console.error('Error loading conversations:', error);
      this.elements.chatHistoryContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; margin: 1rem 0;">Failed to load conversation history.</p>';
    }
  }

  displayConversationHistory(sessions) {
    if (!sessions || sessions.length === 0) {
      this.elements.chatHistoryContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; margin: 1rem 0;">No conversations yet. Start chatting!</p>';
      return;
    }

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const groups = {
      today: [],
      yesterday: [],
      past7days: [],
      older: []
    };

    sessions.forEach(sess => {
      const sessDate = new Date(sess.updated_at);
      const sessDay = new Date(sessDate.getFullYear(), sessDate.getMonth(), sessDate.getDate());

      if (sessDay.getTime() === today.getTime()) {
        groups.today.push(sess);
      } else if (sessDay.getTime() === yesterday.getTime()) {
        groups.yesterday.push(sess);
      } else if (sessDay >= sevenDaysAgo) {
        groups.past7days.push(sess);
      } else {
        groups.older.push(sess);
      }
    });

    let historyHTML = '';

    const groupLabels = {
      today: 'Today',
      yesterday: 'Yesterday',
      past7days: 'Past 7 Days',
      older: 'Older'
    };

    Object.entries(groups).forEach(([groupKey, groupSessions]) => {
      if (groupSessions.length > 0) {
        historyHTML += `
          <div class="history-group">
            <div class="history-group-title">${groupLabels[groupKey]}</div>
            ${groupSessions.map(sess => {
              const title = sess.first_message && sess.first_message.trim() ? this.truncateMessage(sess.first_message, 40) : 'New Chat';
              return `
                <div class="conversation-history-item ${this.activeConversationId === sess.id ? 'active' : ''}"
                     data-conversation-id="${sess.id}"
                     onclick="window.nexusChat.loadConversation('${sess.id}')">
                  <h4>${title}</h4>
                  <p class="conversation-meta">${sess.message_count ? sess.message_count + ' message' + (sess.message_count !== 1 ? 's' : '') + ' • ' : ''}${this.formatChatTime(sess.updated_at)}</p>
                  <div class="conversation-actions">
                    <button onclick="event.stopPropagation(); window.nexusChat.deleteConversation('${sess.id}')" class="delete-btn" title="Delete conversation">
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      }
    });

    this.elements.chatHistoryContainer.innerHTML = historyHTML;
  }

  async loadConversation(sessionId) {
    try {
      this.activeConversationId = sessionId;
      
      // Update active state in UI
      document.querySelectorAll('.conversation-history-item').forEach(item => {
        item.classList.remove('active');
      });
      document.querySelector(`[data-conversation-id="${sessionId}"]`)?.classList.add('active');

      const response = await fetch(`/api/session/${sessionId}`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to load conversation');
      }

      const data = await response.json();
      
      // Clear current messages
      this.elements.messages.innerHTML = '';
      
      // Load all messages in the session
      if (data.messages && data.messages.length > 0) {
        data.messages.forEach(message => {
          // Check if it's a user message or AI message
          if (message.sender === 'user' || message.user_message) {
            this.renderMessage(message.content || message.user_message, 'user', false);
          } else if (message.sender === 'ai' || message.sender === 'assistant' || message.ai_message) {
            this.renderMessage(message.content || message.ai_message, 'ai', false);
          }
        });
      } else {
        this.elements.messages.innerHTML = '<div class="empty-state">No messages in this conversation yet.</div>';
      }

      this.scrollToBottom();
    } catch (error) {
      console.error('Error loading conversation:', error);
      this.renderMessage('Failed to load conversation.', 'ai');
    }
  }

  async createNewConversation() {
    try {
      // Clear current conversation
      this.activeConversationId = null;
      this.activeChatId = null;
      this.elements.messages.innerHTML = '<div class="empty-state">Start a new conversation!</div>';
      
      // Remove active state from all conversations
      document.querySelectorAll('.conversation-history-item').forEach(item => {
        item.classList.remove('active');
      });
      
    } catch (error) {
      console.error('Error creating new conversation:', error);
    }
  }

  async deleteConversation(sessionId) {
    if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`/api/delete_session/${sessionId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to delete conversation');
      }

      // If this was the active conversation, clear the chat area
      if (this.activeConversationId === sessionId) {
        this.createNewConversation();
      }

      // Refresh conversations
      await this.loadConversations();
    } catch (error) {
      console.error('Error deleting conversation:', error);
      alert('Failed to delete conversation. Please try again.');
    }
  }

  async renameConversation(conversationId, currentTitle) {
    const newTitle = prompt('Enter new conversation title:', currentTitle);
    if (!newTitle || newTitle === currentTitle) {
      return;
    }

    try {
      const response = await fetch(`/api/conversations/${conversationId}/title`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ title: newTitle })
      });

      if (!response.ok) {
        throw new Error('Failed to rename conversation');
      }

      // Refresh conversations
      await this.loadConversations();
    } catch (error) {
      console.error('Error renaming conversation:', error);
      alert('Failed to rename conversation. Please try again.');
    }
  }

  async getAIResponse(userText) {
    try {
      console.log('Sending message to AI:', userText);
      
      // Create a session if we don't have an active one
      if (!this.activeConversationId) {
        const sessionResponse = await fetch('/api/new_session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify({
            session_name: userText.substring(0, 50) + (userText.length > 50 ? '...' : '')
          })
        });
        
        if (sessionResponse.ok) {
          const sessionData = await sessionResponse.json();
          this.activeConversationId = sessionData.session_id;
          console.log('Created new session:', this.activeConversationId);
        }
      } else {
        // Check if this is the first real message for an existing "New Chat" session
        // Update session name to use the first meaningful message
        try {
          await fetch(`/api/session/${this.activeConversationId}/update-name`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
              session_name: userText.substring(0, 50) + (userText.length > 50 ? '...' : '')
            })
          });
        } catch (error) {
          console.log('Session name update failed (non-critical):', error);
        }
      }
      
      const response = await fetch('/api/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          session_id: this.activeConversationId,
          content: userText,
          file_id: this.activeFileId
        })
      });

      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('API Error:', errorData);
        throw new Error(errorData.error || `Request failed with status ${response.status}`);
      }

      const data = await response.json();
      console.log('AI Response received:', data);
      
      return data.ai_message || data.response || 'Sorry, I could not generate a response.';
    } catch (error) {
      console.error('Error getting AI response:', error);
      return `I apologize, but I'm having trouble connecting to the AI service: ${error.message}`;
    }
  }

  async saveChatToBackend(userMessage, aiMessage) {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_message: userMessage, ai_message: aiMessage })
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const newChat = await response.json();
      this.activeChatId = newChat.id;

      // Refresh the chat history to include the new chat
      this.loadChatHistory();
    } catch (error) {
      console.error('Error saving chat:', error);
    }
  }

  handleFileSelection(event) {
    const file = event.target.files[0];
    if (file) {
      this.elements.filePreview.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
      this.elements.filePreview.style.display = 'block';
      this.elements.fileUploadSection.classList.add('active');
    }
  }

  async handleFileUpload(file = null) {
    // Single file upload fallback (for manual calls)
    if (!file) return;
    await this.uploadMultipleFiles([file]);
  }

  async uploadMultipleFiles(files) {
    if (!files || !files.length) return;
    this.elements.uploadBtn?.setAttribute('disabled', true);
    if (this.elements.uploadBtn) this.elements.uploadBtn.textContent = 'Uploading...';

    try {
      // Create a session if we don't have an active one
      if (!this.activeConversationId) {
        const sessionResponse = await fetch('/api/new_session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ session_name: `New Chat` })
        });
        if (sessionResponse.ok) {
          const sessionData = await sessionResponse.json();
          this.activeConversationId = sessionData.session_id;
        } else {
          let errorMsg = `Failed to create session for file upload (status ${sessionResponse.status})`;
          try {
            const errJson = await sessionResponse.json();
            if (errJson && errJson.error) errorMsg += `: ${errJson.error}`;
          } catch {}
          throw new Error(errorMsg);
        }
      }

      let uploadCount = 0;
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', this.activeConversationId);

        const response = await fetch('/api/upload', {
          method: 'POST',
          credentials: 'include',
          body: formData
        });

        if (!response.ok) {
          let errorMsg = `❌ Upload failed for ${file.name} (status ${response.status})`;
          try {
            const errorData = await response.json();
            if (errorData && errorData.error) errorMsg += `: ${errorData.error}`;
          } catch {}
          this.renderMessage(errorMsg, 'ai');
          continue;
        }

  const data = await response.json();
  this.activeFileId = data.file_id;
  this.updateActiveFileUI(data.filename);
  // Only show a simple message
  this.renderMessage('File uploaded successfully.', 'ai');
  uploadCount++;
      }
      if (uploadCount > 1) {
        this.renderMessage('Files uploaded successfully.', 'ai');
      }
    } catch (error) {
      console.error('Upload error:', error);
      this.renderMessage(`❌ Upload failed: ${error.message}`, 'ai');
    } finally {
      this.elements.uploadBtn?.removeAttribute('disabled');
      if (this.elements.uploadBtn) this.elements.uploadBtn.textContent = '📁 Upload File';
      this.elements.fileInput.value = '';
      this.clearFilePreview();
    }
  }


  updateActiveFileUI(filename) {
    const indicator = this.elements.activeFileIndicator;
    const nameSpan = document.getElementById('active-file-name');
    const analyzeBtn = document.getElementById('analyze-image-btn');
    
    if (nameSpan) {
      nameSpan.textContent = filename;
    }
    
    // Show analyze button for image files
    const isImage = /\.(png|jpg|jpeg|gif|webp)$/i.test(filename);
    if (analyzeBtn) {
      analyzeBtn.style.display = isImage ? 'inline-block' : 'none';
    }
    
    indicator.style.display = 'flex';
  }

  clearFilePreview() {
    this.elements.filePreview.style.display = 'none';
    this.elements.fileUploadSection.classList.remove('active');
  }

  renderMessage(text, sender, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    // Create avatar element
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    
    if (sender === 'user') {
      // Use user's avatar or initials
      if (this.currentUser && this.currentUser.avatar && this.currentUser.avatar !== '/static/Avatar.jpeg') {
        avatarDiv.innerHTML = `<img src="${this.currentUser.avatar}" alt="User Avatar" class="avatar-image">`;
      } else {
        const initials = this.currentUser && this.currentUser.username ? 
          this.currentUser.username.substring(0, 2).toUpperCase() : 'U';
        avatarDiv.innerHTML = `<span class="avatar-initials">${initials}</span>`;
      }
    } else {
      // AI avatar
      avatarDiv.innerHTML = '<span class="ai-avatar">🤖</span>';
    }

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = text;

    // Create message wrapper for content and timestamp
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper';
    messageWrapper.appendChild(messageContent);

    if (timestamp) {
      const timestampDiv = document.createElement('div');
      timestampDiv.className = 'message-timestamp';
      timestampDiv.textContent = timestamp;
      messageWrapper.appendChild(timestampDiv);
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(messageWrapper);

    this.elements.messages.appendChild(messageDiv);
    this.scrollToBottom();
  }

  showTypingIndicator(show) {
    this.elements.typingIndicator.style.display = show ? 'block' : 'none';
    if (show) {
      this.scrollToBottom();
    }
  }

  scrollToBottom() {
    this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
  }

  async loadSpecificChat(chatId) {
    // Legacy method - find the conversation containing this chat
    try {
      const response = await fetch(`/api/chats/${chatId}`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const chatData = await response.json();
        if (chatData.conversation_id) {
          await this.loadConversation(chatData.conversation_id);
        }
      }
    } catch (error) {
      console.error('Error loading specific chat:', error);
    }
  }

  startNewChat() {
    this.createNewConversation();
  }

  async exportChatHistory() {
    try {
      const response = await fetch('/api/chats/export', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `nexuschat-chat-history-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        this.renderMessage('Chat history exported successfully!', 'ai');
      } else {
        let errorMsg = 'Export failed: ';
        try {
          errorMsg += await response.text();
        } catch (e) {
          errorMsg += 'Unknown error.';
        }
        this.renderMessage(errorMsg, 'ai');
      }
    } catch (error) {
      console.error('Export failed:', error);
      this.renderMessage(`Export failed: ${error.message}`, 'ai');
    }
  }

  startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    // Helper to always reset the button
    const resetVoiceBtn = () => {
      this.elements.voiceBtn.textContent = '🎤';
      this.elements.voiceBtn.disabled = false;
    };

    recognition.onstart = () => {
      this.elements.voiceBtn.textContent = '🔴';
      this.elements.voiceBtn.disabled = true;
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      this.elements.userInput.value = transcript;
      this.elements.userInput.focus();
      // Always re-enable send button after speech
      this.elements.sendBtn.disabled = false;
      resetVoiceBtn();
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      alert('Speech recognition error: ' + event.error);
      resetVoiceBtn();
    };

    recognition.onend = () => {
      resetVoiceBtn();
    };

    recognition.start();
  }
}

// Initialize the bot when the page loads
document.addEventListener('DOMContentLoaded', () => {
  window.nexusChat = new NexusChat();
});

// Global function for clearing active file (called from HTML)
function clearActiveFile() {
  if (window.nexusChat) {
    window.nexusChat.activeFileId = null;
    document.getElementById('active-file-indicator').style.display = 'none';
  }
}

// Legacy file analysis functions removed - now handled by backend API
// 🔍 Search chat button functionality
document.getElementById('search-chat-btn')?.addEventListener('click', () => {
  const searchModal = document.getElementById('search-modal');
  const searchInput = document.getElementById('search-input');
  searchModal.classList.add('show');
  searchInput.focus();
});

document.getElementById('close-search-modal')?.addEventListener('click', () => {
  const searchModal = document.getElementById('search-modal');
  const searchInput = document.getElementById('search-input');
  const searchResults = document.getElementById('search-results');
  searchModal.classList.remove('show');
  searchInput.value = '';
  searchResults.innerHTML = '<div class="no-results">Type to search your chat history...</div>';
});

document.getElementById('search-modal')?.addEventListener('click', (e) => {
  if (e.target.id === 'search-modal') {
    document.getElementById('search-modal').classList.remove('show');
  }
});

let searchTimeout;
document.getElementById('search-input')?.addEventListener('input', (e) => {
  clearTimeout(searchTimeout);
  const query = e.target.value.trim();
  const resultsBox = document.getElementById('search-results');

  if (!query) {
    resultsBox.innerHTML = '<div class="no-results">Type to search your chat history...</div>';
    return;
  }

  searchTimeout = setTimeout(() => {
    searchChatHistory(query);
  }, 300);
});

async function searchChatHistory(query) {
  const resultsBox = document.getElementById('search-results');
  try {
    resultsBox.innerHTML = '<div class="no-results">Searching...</div>';

    const response = await fetch(`/api/chats/search?q=${encodeURIComponent(query)}`, {
      credentials: 'include'
    });

    if (response.ok) {
      const results = await response.json();
      displaySearchResults(results);
    } else {
      resultsBox.innerHTML = '<div class="no-results">Server search failed. Searching locally...</div>';
      performClientSideSearch(query);
    }
  } catch (error) {
    console.error('Search error:', error);
    resultsBox.innerHTML = '<div class="no-results">Server error. Searching locally...</div>';
    performClientSideSearch(query);
  }
}

function performClientSideSearch(query) {
  const chatItems = document.querySelectorAll('.chat-history-item');
  const results = [];

  chatItems.forEach(item => {
    const title = item.querySelector('h4')?.textContent?.toLowerCase() || '';
    if (title.includes(query.toLowerCase())) {
      results.push({
        id: item.dataset.chatId,
        user_message: item.querySelector('h4')?.textContent || '',
        timestamp: item.querySelector('p')?.textContent || ''
      });
    }
  });

  displaySearchResults({ results });
}

function displaySearchResults(results) {
  const resultsBox = document.getElementById('search-results');
  if (!results || results.results.length === 0) {
    resultsBox.innerHTML = '<div class="no-results">No results found.</div>';
    return;
  }

  const resultsHTML = results.results.map(result => `
    <div class="search-result-item" data-session-id="${result.session_id}" onclick="loadSearchResult('${result.session_id}')">
      <h4>${(result.content || result.session_name).substring(0, 100)}${(result.content || result.session_name).length > 100 ? '...' : ''}</h4>
      <p class="search-meta">${result.sender === 'user' ? '👤' : '🤖'} ${result.session_name} • ${new Date(result.timestamp).toLocaleDateString()}</p>
    </div>
  `).join('');

  resultsBox.innerHTML = resultsHTML;
}

function loadSearchResult(sessionId) {
  document.getElementById('search-modal').classList.remove('show');
  if (window.nexusChat && window.nexusChat.loadConversation) {
    window.nexusChat.loadConversation(parseInt(sessionId));
  }
}
