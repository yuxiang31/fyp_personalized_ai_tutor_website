class ChatWebSocket {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.messageQueue = [];
        this.currentThreadId = null;
        this.csrfToken = this.getCsrfToken();
        this.init();
    }

    init() {
        this.setupElements();
        this.setupEventListeners();
        this.initializeThreadId();
        // Fetch and render initial conversation history client-side
        if (this.currentThreadId) {
            this.switchConversation(this.currentThreadId);
        }
        this.connect();
    }

    setupElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatTitleEl = document.getElementById('chatTitle');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.historyContainer = document.getElementById('historyContainer');
        this.newChatButton = document.getElementById('newChatBtn');
        this.sidebar = document.querySelector('.sidebar');
        this.sidebarResizer = document.getElementById('sidebarResizer');
        this.chatContainer = document.querySelector('.chat-container');

        // Initialize browser tab title from current header title
        if (this.chatTitleEl && this.chatTitleEl.textContent) {
            document.title = `${this.chatTitleEl.textContent} | AI Tutor`;
        }
    }

    getCsrfToken() {
        const csrfCookie = document.cookie
            .split(';')
            .find(cookie => cookie.trim().startsWith('csrftoken='));
        return csrfCookie ? csrfCookie.split('=')[1] : '';
    }

    initializeThreadId() {
        // Get thread_id from chat messages container
        if (this.chatMessages) {
            this.currentThreadId = this.chatMessages.getAttribute('data-thread-id');
        }
    }

    setupEventListeners() {
        // Send button click
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }

        // New chat button click
        if (this.newChatButton) {
            this.newChatButton.addEventListener('click', () => this.createNewChat());
        }

        if (this.historyContainer) {
            this.historyContainer.addEventListener('click', (e) => {
                // Handle delete click first
                const deleteBtn = e.target.closest('.delete-conversation-btn');
                if (deleteBtn) {
                    const threadId = deleteBtn.getAttribute('data-thread-id');
                    this.confirmAndDeleteConversation(threadId, deleteBtn);
                    e.stopPropagation();
                    return;
                }

                const historyItem = e.target.closest('.history-item');
                if (historyItem) {
                    const threadId = historyItem.getAttribute('data-thread-id');
                    this.switchConversation(threadId);
                }
            });
        }

        // Enter key to send (Shift+Enter for new line)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea (grow up to CSS max-height, then scroll)
        this.messageInput.addEventListener('input', () => {
            const computed = window.getComputedStyle(this.messageInput);
            // Resolve CSS max-height number (fallback to 160px if none)
            const maxH = parseInt(computed.maxHeight || '160', 10) || 160;
            this.messageInput.style.height = 'auto';
            const target = Math.min(this.messageInput.scrollHeight, maxH);
            this.messageInput.style.height = target + 'px';
        });

        // Retry connection on window focus (if disconnected)
        window.addEventListener('focus', () => {
            if (!this.isConnected) {
                this.connect();
            }
        });

        // Sidebar resizing
        if (this.sidebar && this.sidebarResizer) {
            const setSidebarWidth = (pxOrStr) => {
                const val = typeof pxOrStr === 'number' ? pxOrStr + 'px' : String(pxOrStr);
                this.sidebar.style.width = val;
                if (this.chatContainer) {
                    const disp = window.getComputedStyle(this.chatContainer).display;
                    if (disp.includes('grid')) {
                        const num = parseInt(val, 10);
                        if (!Number.isNaN(num)) {
                            // Assume 2-column grid: [sidebar][main]
                            this.chatContainer.style.gridTemplateColumns = `${num}px 1fr`;
                        }
                    }
                }
            };
            // Restore width from localStorage
            const saved = localStorage.getItem('sidebarWidth');
            if (saved) setSidebarWidth(saved);

            let startX = 0;
            let startWidth = 0;
            const min = 180; // px
            const max = 480; // px
            const onMove = (e) => {
                const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                const delta = clientX - startX;
                const next = Math.min(max, Math.max(min, startWidth + delta));
                setSidebarWidth(next);
            };
            const onUp = () => {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                document.removeEventListener('touchmove', onMove);
                document.removeEventListener('touchend', onUp);
                this.sidebarResizer.classList.remove('dragging');
                if (this.sidebar && this.sidebar.style.width) localStorage.setItem('sidebarWidth', this.sidebar.style.width);
            };
            const onDown = (e) => {
                startX = e.touches ? e.touches[0].clientX : e.clientX;
                startWidth = this.sidebar.getBoundingClientRect().width;
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
                document.addEventListener('touchmove', onMove, { passive: false });
                document.addEventListener('touchend', onUp);
                this.sidebarResizer.classList.add('dragging');
                e.preventDefault();
            };
            this.sidebarResizer.addEventListener('mousedown', onDown);
            this.sidebarResizer.addEventListener('touchstart', onDown, { passive: false });
            // Keyboard support: left/right to resize
            this.sidebarResizer.addEventListener('keydown', (e) => {
                if (!this.sidebar) return;
                const rect = this.sidebar.getBoundingClientRect();
                let width = rect.width;
                const step = (e.shiftKey ? 20 : 10);
                if (e.key === 'ArrowLeft') width = Math.max(180, width - step);
                if (e.key === 'ArrowRight') width = Math.min(480, width + step);
                if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                    setSidebarWidth(width);
                    localStorage.setItem('sidebarWidth', this.sidebar.style.width);
                    e.preventDefault();
                }
            });
            // Double-click to reset width
            this.sidebarResizer.addEventListener('dblclick', () => {
                const def = 280;
                setSidebarWidth(def);
                localStorage.setItem('sidebarWidth', def + 'px');
            });
        }
    }

    async confirmAndDeleteConversation(threadId, deleteBtnEl) {
        const confirmed = window.confirm('Delete this conversation? This cannot be undone.');
        if (!confirmed) return;

        try {
            const response = await fetch(`/chat/conversation/${threadId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to delete');
            }

            // Remove from UI
            const item = deleteBtnEl.closest('.history-item');
            const wasActive = item && item.classList.contains('active');
            if (item) item.remove();

            // If it was the active conversation, pick another one
            if (wasActive) {
                const firstItem = this.historyContainer.querySelector('.history-item');
                if (firstItem) {
                    const nextThread = firstItem.getAttribute('data-thread-id');
                    this.switchConversation(nextThread);
                } else {
                    // No conversations left; create a new one
                    await this.createNewChat();
                }
            }

            // If deleted thread equals currentThreadId, clear messages too
            if (this.currentThreadId === threadId && this.chatMessages) {
                this.chatMessages.innerHTML = '';
            }
        } catch (err) {
            console.error('Delete failed:', err);
            this.showSystemMessage('Failed to delete conversation', 'error');
        }
    }

    async createNewChat() {
        try {
            const response = await fetch('/chat/create-conversation/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                // Update current thread ID
                this.currentThreadId = data.thread_id;

                // Clear current chat messages
                if (this.chatMessages) {
                    this.chatMessages.innerHTML = '';
                }

                // Update WebSocket with new thread
                if (this.isConnected) {
                    this.sendThreadUpdate(data.thread_id);
                }

                // Add new conversation to history
                this.addConversationToHistory(data);

                // Update header title immediately
                this.updateConversationTitleUI(data.thread_id, data.conversation_title || 'New Chat');

                // Update URL
                this.updateURL(data.thread_id);

                // Clear message input
                if (this.messageInput) {
                    this.messageInput.value = '';
                    this.messageInput.style.height = 'auto';
                }
            } else {
                console.error('Failed to create new conversation:', data.error);
                this.showError('Failed to create new conversation');
            }
        } catch (error) {
            console.error('Error creating new conversation:', error);
            this.showError('Error creating new conversation');
        }
    }

    addConversationToHistory(conversation) {
        if (this.historyContainer) {
            // Create new history item
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item active';
            historyItem.setAttribute('data-thread-id', conversation.thread_id);

            const title = document.createElement('span');
            title.className = 'conversation-title';
            title.textContent = conversation.conversation_title || 'New Chat';

            const date = document.createElement('span');
            date.className = 'conversation-date';
            try {
                const d = new Date(conversation.created_at);
                date.textContent = d.toLocaleDateString(undefined, { month: 'short', day: '2-digit', year: 'numeric' });
            } catch (_) {
                date.textContent = '';
            }

            const delBtn = document.createElement('button');
            delBtn.className = 'delete-conversation-btn';
            delBtn.title = 'Delete conversation';
            delBtn.setAttribute('aria-label', 'Delete conversation');
            delBtn.setAttribute('data-thread-id', conversation.thread_id);
            delBtn.textContent = '×';

            // Assemble history item
            historyItem.appendChild(title);
            historyItem.appendChild(date);
            historyItem.appendChild(delBtn);
            
            // Remove active class from other items
            const activeItems = this.historyContainer.querySelectorAll('.history-item.active');
            activeItems.forEach(item => item.classList.remove('active'));
            
            // Add new conversation at the top of history
            if (this.historyContainer.firstChild) {
                this.historyContainer.insertBefore(historyItem, this.historyContainer.firstChild);
            } else {
                this.historyContainer.appendChild(historyItem);
            }
        }
    }

    updateURL(threadId) {
        // Update URL without reloading the page
        const newUrl = window.location.pathname + '?thread=' + threadId;
        window.history.pushState({ threadId }, '', newUrl);
    }

    async switchConversation(threadId) {
        this.currentThreadId = threadId;
        
        // Update active state in history
        if (this.historyContainer) {
            const activeItems = this.historyContainer.querySelectorAll('.history-item.active');
            activeItems.forEach(item => item.classList.remove('active'));
            
            const newActiveItem = this.historyContainer.querySelector(`[data-thread-id="${threadId}"]`);
            if (newActiveItem) {
                newActiveItem.classList.add('active');
            }
        }

        // Fetch conversation history
        try {
            const response = await fetch(`/chat/conversation/${threadId}`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                // Clear current chat messages
                if (this.chatMessages) {
                    this.chatMessages.innerHTML = '';
                }

                // Add messages from history
                if (data.conversation.checkpoints) {
                    data.conversation.checkpoints.forEach(checkpoint => {
                        if (checkpoint.type=="human"){
                            checkpoint.type="user"
                        }
                        this.addMessage(checkpoint.old_message, checkpoint.type);
                    });
                }

                // Update WebSocket
                if (this.isConnected) {
                    this.sendThreadUpdate(threadId);
                }

                // Update URL
                this.updateURL(threadId);

                // Update header title from server response
                if (this.chatTitleEl && data.conversation && data.conversation.title) {
                    this.chatTitleEl.textContent = data.conversation.title;
                    document.title = `${data.conversation.title} | AI Tutor`;
                }
            } else {
                console.error('Failed to fetch conversation history:', data.error);
                this.showSystemMessage('Failed to load conversation history', 'error');
            }
        } catch (error) {
            console.error('Error fetching conversation history:', error);
            this.showSystemMessage('Error loading conversation history', 'error');
        }
    }

    sendThreadUpdate(threadId) {
        try {
            this.socket.send(JSON.stringify({
                type: 'thread_update',
                thread_id: threadId
            }));
        } catch (error) {
            console.error('Error sending thread update:', error);
        }
    }

    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/chat/`;
            
            this.socket = new WebSocket(wsUrl);
            this.setupSocketEventListeners();
            
            this.updateConnectionStatus('connecting', 'Connecting...');
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleConnectionError('Failed to establish connection');
        }
    }

    setupSocketEventListeners() {
        this.socket.onopen = () => {
            console.log('WebSocket connection established');
            this.isConnected = true;
            this.updateConnectionStatus('connected', 'Connected');

            // Send initial thread_id when connection is established
            if (this.currentThreadId) {
                this.sendThreadUpdate(this.currentThreadId);
            }

            this.processMessageQueue();
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket connection closed:', event.code, event.reason);
            this.isConnected = false;
            this.updateConnectionStatus('disconnected', 'Disconnected');
            
            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
                if (!this.isConnected) {
                    this.connect();
                }
            }, 3000);
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.handleConnectionError('Connection error occurred');
        };
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        if (!this.isConnected) {
            this.messageQueue.push(message);
            this.showSystemMessage('Message queued. Attempting to reconnect...', 'warning');
            this.connect();
            return;
        }

        try {
            this.socket.send(JSON.stringify({
                type: 'chat',
                message: message,
                thread_id: this.currentThreadId
            }));

            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
            this.messageInput.focus();
        } catch (error) {
            console.error('Error sending message:', error);
            this.showSystemMessage('Failed to send message', 'error');
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'chat_message':
                this.addMessage(data.message, data.sender);
                break;
            case 'typing_indicator':
                this.showTypingIndicator(data.is_typing);
                break;
            case 'connection_status':
                this.showSystemMessage(data.message, 'success');
                break;
            case 'title_update':
                this.updateConversationTitleUI(data.thread_id, data.conversation_title);
                break;
            case 'error':
                this.showSystemMessage(data.message, 'error');
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    updateConversationTitleUI(threadId, newTitle) {
        // Update header title
        const header = this.chatTitleEl || document.getElementById('chatTitle');
        if (header) header.textContent = newTitle || 'AI Tutor Chat';
        // Update document title
        if (newTitle) {
            document.title = `${newTitle} | AI Tutor`;
        }

        // Update sidebar history title for the matching item
        if (!this.historyContainer) return;
        const item = this.historyContainer.querySelector(`.history-item[data-thread-id="${threadId}"]`);
        if (!item) return;
        const titleEl = item.querySelector('.conversation-title');
        if (titleEl) titleEl.textContent = newTitle || 'New Chat';
    }

    addMessage(message, sender) {
        const wrapper = document.createElement('div');
        wrapper.className = `message ${sender}`;

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        // Add sender label
        const label = document.createElement('div');
        label.className = 'sender-name';
        // Normalize sender names
        const s = (sender || '').toLowerCase();
        let displayName = 'User';
        if (s === 'assistant' || s === 'bot' || s === 'ai' || s === 'system') displayName = 'AI Tutor';
        if (s === 'user' || s === 'human') displayName = 'You';
        label.textContent = displayName;
        bubble.appendChild(label);

        // Message content
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = this.renderMessageContent(message);
        bubble.appendChild(content);

        wrapper.appendChild(bubble);
        this.chatMessages.appendChild(wrapper);
        this.scrollToBottom();
    }

    // --- helpers to render safe, clickable content ---
    escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    linkifySafe(text) {
        // Match http(s) URLs or site-root relative paths like /static/...
        const urlRegex = /(https?:\/\/[^\s<]+|\/[A-Za-z0-9_\/$\-.%?=&#]+)/g;
        const parts = String(text).split(urlRegex);
        let html = '';
        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            if (i % 2 === 1) {
                // This is a URL match
                const url = part;
                const safeHref = url.replace(/\"/g, '%22');
                const display = this.escapeHtml(url);
                html += `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${display}</a>`;
            } else {
                // Normal text: escape + convert newlines
                html += this.escapeHtml(part).replace(/\n/g, '<br>');
            }
        }
        return html;
    }

    renderMessageContent(message) {
        // If the message looks like JSON with a download_url, render a friendly anchor
        try {
            const obj = JSON.parse(message);
            if (obj && typeof obj === 'object' && obj.download_url) {
                const href = String(obj.download_url);
                const label = obj.file_name || 'Download study plan (.docx)';
                const extra = obj.study_material_id ? ` <small>(ID: ${this.escapeHtml(obj.study_material_id)})</small>` : '';
                return `<div>Your file is ready: <a href="${href}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(label)}</a>.${extra}</div>`;
            }
        } catch (_) {
            // not JSON; fall back
        }
        return this.linkifySafe(message);
    }

    showTypingIndicator(isTyping) {
        // Remove existing typing indicator if any
        const existingIndicator = this.chatMessages.querySelector('.typing-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        if (isTyping) {
            // Create new typing indicator
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator show';
            typingIndicator.innerHTML = `
                <div class="typing-bubble">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            `;
            
            // Append to chat messages
            this.chatMessages.appendChild(typingIndicator);
            this.scrollToBottom();
        }
    }

    showSystemMessage(message, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `error-message ${type}`;
        messageDiv.textContent = message;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Auto-remove system messages after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 5000);
    }

    updateConnectionStatus(status, text) {
        this.statusIndicator.className = `status-indicator ${status}`;
        this.statusText.textContent = text;

        if (status === 'connected') {
            this.sendButton.disabled = false;
            this.messageInput.disabled = false;
        } else {
            this.sendButton.disabled = true;
            this.messageInput.disabled = false; // Keep enabled for queuing messages
        }
    }

    handleConnectionError(message) {
        this.showSystemMessage(message, 'error');
        this.updateConnectionStatus('disconnected', 'Connection Failed');
    }

    processMessageQueue() {
        while (this.messageQueue.length > 0 && this.isConnected) {
            const message = this.messageQueue.shift();
            setTimeout(() => {
                this.messageInput.value = message;
                this.sendMessage();
            }, 100);
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 50);
    }
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatWebSocket();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.chatApp && !window.chatApp.isConnected) {
        window.chatApp.connect();
    }
});

document.getElementById('logoutBtn').addEventListener('click', function() {
    if (confirm('Are you sure you want to logout?')) {
        // Implement logout functionality
        window.location.href = 'logout';
    }
});

