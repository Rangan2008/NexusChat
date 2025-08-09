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
    this.elements.fileInput?.addEventListener('change', (e) => {
      this.handleFileUpload(e.target.files[0]);
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
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const chatDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    if (chatDay.getTime() === today.getTime()) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleDateString();
    }
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
      const response = await fetch('/api/conversations', {
        method: 'GET',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to fetch conversations');
      }

      const data = await response.json();
      this.conversations = data.conversations;
      this.displayConversationHistory(data.conversations);
    } catch (error) {
      console.error('Error loading conversations:', error);
      this.elements.chatHistoryContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; margin: 1rem 0;">Failed to load conversation history.</p>';
    }
  }

  displayConversationHistory(conversations) {
    if (!conversations || conversations.length === 0) {
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

    conversations.forEach(conv => {
      const convDate = new Date(conv.updated_at);
      const convDay = new Date(convDate.getFullYear(), convDate.getMonth(), convDate.getDate());

      if (convDay.getTime() === today.getTime()) {
        groups.today.push(conv);
      } else if (convDay.getTime() === yesterday.getTime()) {
        groups.yesterday.push(conv);
      } else if (convDay >= sevenDaysAgo) {
        groups.past7days.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    let historyHTML = '';

    const groupLabels = {
      today: 'Today',
      yesterday: 'Yesterday',
      past7days: 'Past 7 Days',
      older: 'Older'
    };

    Object.entries(groups).forEach(([groupKey, groupConversations]) => {
      if (groupConversations.length > 0) {
        historyHTML += `
          <div class="history-group">
            <div class="history-group-title">${groupLabels[groupKey]}</div>
            ${groupConversations.map(conv => `
              <div class="conversation-history-item ${this.activeConversationId === conv.id ? 'active' : ''}" 
                   data-conversation-id="${conv.id}" 
                                      onclick="window.nexusChat.loadConversation(${conv.id})"&gt;
                <h4>${this.truncateMessage(conv.title || 'Untitled Conversation', 40)}</h4>
                <p class="conversation-meta">${conv.chat_count} message${conv.chat_count !== 1 ? 's' : ''} • ${this.formatChatTime(conv.updated_at)}</p>
                <div class="conversation-actions">
                  <button onclick="event.stopPropagation(); window.nexusChat.deleteConversation(${conv.id})" class="delete-btn" title="Delete conversation">
                    <i class="fas fa-trash"></i>
                  </button>
                  <button onclick="event.stopPropagation(); window.nexusChat.renameConversation(${conv.id}, '${conv.title.replace(/'/g, "\\'")}');" class="rename-btn" title="Rename conversation">
                    <i class="fas fa-edit"></i>
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        `;
      }
    });

    this.elements.chatHistoryContainer.innerHTML = historyHTML;
  }

  async loadConversation(conversationId) {
    try {
      this.activeConversationId = conversationId;
      
      // Update active state in UI
      document.querySelectorAll('.conversation-history-item').forEach(item => {
        item.classList.remove('active');
      });
      document.querySelector(`[data-conversation-id="${conversationId}"]`)?.classList.add('active');

      const response = await fetch(`/api/conversations/${conversationId}`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to load conversation');
      }

      const data = await response.json();
      
      // Clear current messages
      this.elements.messages.innerHTML = '';
      
      // Load all chats in the conversation
      data.chats.forEach(chat => {
        this.renderMessage(chat.user_message, 'user', false);
        this.renderMessage(chat.ai_message, 'ai', false);
      });

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

  async deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to delete conversation');
      }

      // If this was the active conversation, clear the chat area
      if (this.activeConversationId === conversationId) {
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
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          message: userText,
          file_id: this.activeFileId,
          conversation_id: this.activeConversationId // Include current conversation
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
      
      // Update conversation info
      this.activeConversationId = data.conversation_id;
      this.activeChatId = data.chat_id;
      
      return data.response || 'Sorry, I could not generate a response.';
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
    const selectedFile = file || this.elements.fileInput?.files?.[0];
    if (!selectedFile) {
      alert('Please select a file first.');
      return;
    }

    this.elements.uploadBtn?.setAttribute('disabled', true);
    this.elements.uploadBtn && (this.elements.uploadBtn.textContent = 'Uploading...');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch('/api/files', {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || response.statusText);
      }

      const data = await response.json();
      this.activeFileId = data.file_id;
      this.updateActiveFileUI(data.filename);
      this.renderMessage(`📄 File "${data.filename}" uploaded successfully. You can now ask questions about it.`, 'ai');

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
    if (nameSpan) {
      nameSpan.textContent = filename;
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
        throw new Error(await response.text());
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

    recognition.onstart = () => {
      this.elements.voiceBtn.textContent = '🔴';
      this.elements.voiceBtn.disabled = true;
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      this.elements.userInput.value = transcript;
      this.elements.userInput.focus();
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      alert('Speech recognition error: ' + event.error);
    };

    recognition.onend = () => {
      this.elements.voiceBtn.textContent = '🎤';
      this.elements.voiceBtn.disabled = false;
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
      performClientSideSearch(query);
    }
  } catch (error) {
    console.error('Search error:', error);
    performClientSideSearch(query);
  }
}

function performClientSideSearch(query) {
  const chatItems = document.querySelectorAll('.chat-history-item');
  const results = [];

  chatItems.forEach(item => {
    const title = item.querySelector('h4').textContent.toLowerCase();
    if (title.includes(query.toLowerCase())) {
      results.push({
        id: item.dataset.chatId,
        user_message: item.querySelector('h4').textContent,
        timestamp: item.querySelector('p').textContent
      });
    }
  });

  displaySearchResults(results);
}

function displaySearchResults(results) {
  const resultsBox = document.getElementById('search-results');
  if (!results || results.length === 0) {
    resultsBox.innerHTML = '<div class="no-results">No results found.</div>';
    return;
  }

  const resultsHTML = results.map(result => `
    <div class="search-result-item" data-chat-id="${result.id}" onclick="loadSearchResult('${result.id}')">
      <h4>${result.user_message.substring(0, 100)}${result.user_message.length > 100 ? '...' : ''}</h4>
      <p>${new Date(result.timestamp).toLocaleDateString()}</p>
    </div>
  `).join('');

  resultsBox.innerHTML = resultsHTML;
}

function loadSearchResult(chatId) {
  document.getElementById('search-modal').classList.remove('show');
  if (window.nexusChat && window.nexusChat.loadSpecificChat) {
    window.nexusChat.loadSpecificChat(chatId);
  }
}
