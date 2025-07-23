/**
 * Chat UI Frontend Application
 * Vanilla JavaScript implementation with WebSocket communication
 */

class ChatUI {
    constructor() {
        this.websocket = null;
        this.currentModel = null;
        this.user = null;
        this.appName = 'Chat UI';
        this.models = [];
        this.tools = [];
        
        this.initializeMarkdown();
        this.initializeElements();
        this.attachEventListeners();
        this.connectWebSocket();
        this.loadConfig();
    }
    
    initializeMarkdown() {
        // Configure marked with custom renderer for code blocks
        if (typeof marked !== 'undefined') {
            const renderer = new marked.Renderer();
            
            // Custom code block renderer to add copy functionality
            renderer.code = function(code, language) {
                const escapedCode = code.replace(/&/g, '&amp;')
                                      .replace(/</g, '&lt;')
                                      .replace(/>/g, '&gt;')
                                      .replace(/"/g, '&quot;')
                                      .replace(/'/g, '&#39;');
                
                return `<div class="code-block-container">
                    <pre><code class="language-${language || 'text'}">${escapedCode}</code></pre>
                    <button class="copy-button" onclick="copyCodeBlock(this)" title="Copy code">Copy</button>
                </div>`;
            };
            
            marked.setOptions({
                renderer: renderer,
                highlight: null,
                breaks: true,
                gfm: true
            });
        }
    }
    
    initializeElements() {
        this.elements = {
            appTitle: document.querySelector('.header h1'),
            userEmail: document.getElementById('user-email'),
            toolsList: document.getElementById('tools-list'),
            connectionStatus: document.getElementById('connection-status'),
            messages: document.getElementById('messages'),
            messageInput: document.getElementById('message-input'),
            sendButton: document.getElementById('send-button'),
            
            // Dropdown elements
            modelButton: document.getElementById('model-button'),
            modelDropdown: document.getElementById('model-dropdown'),
            selectedModel: document.getElementById('selected-model'),
            
            // Tools panel elements
            toggleToolsPanel: document.getElementById('toggle-tools-panel'),
            closeToolsPanel: document.getElementById('close-tools-panel'),
            toolsPanel: document.getElementById('tools-panel')
        };
    }
    
    attachEventListeners() {
        this.elements.sendButton.addEventListener('click', () => this.sendMessage());
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.elements.messageInput.addEventListener('input', () => {
            this.updateSendButton();
            this.autoResizeTextarea();
        });
        
        // Dropdown functionality
        this.elements.modelButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });
        
        // Tools panel functionality
        this.elements.toggleToolsPanel.addEventListener('click', () => this.toggleToolsPanel());
        this.elements.closeToolsPanel.addEventListener('click', () => this.closeToolsPanel());
        
        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            this.closeDropdown();
        });
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
        };
        
        this.websocket.onmessage = (event) => {
            this.handleWebSocketMessage(JSON.parse(event.data));
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
    }
    
    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            this.appName = config.app_name || 'Chat UI';
            this.models = config.models || [];
            this.tools = config.tools || [];
            this.user = config.user || 'Unknown';
            
            this.updateUI();
        } catch (error) {
            console.error('Error loading config:', error);
            this.showError('Failed to load configuration');
        }
    }
    
    updateUI() {
        // Update page title
        document.title = this.appName;
        
        // Update app title
        this.elements.appTitle.textContent = this.appName;
        
        // Update user info
        this.elements.userEmail.textContent = this.user;
        
        // Update welcome message
        this.updateWelcomeMessage();
        
        // Update models dropdown
        this.updateModelsDropdown();
        
        // Update tools list
        this.updateToolsList();
    }
    
    updateWelcomeMessage() {
        const welcomeMessage = this.elements.messages.querySelector('.message.assistant');
        if (welcomeMessage) {
            const authorElement = welcomeMessage.querySelector('.message-author');
            const contentElement = welcomeMessage.querySelector('.message-content p');
            
            if (authorElement) authorElement.textContent = this.appName;
            if (contentElement) contentElement.textContent = `Welcome to ${this.appName}! Select a model and start chatting. You can also explore available tools in the side panel.`;
        }
    }
    
    updateModelsDropdown() {
        if (this.models.length === 0) {
            this.elements.modelDropdown.innerHTML = '<div class="dropdown-option">No models available</div>';
            return;
        }
        
        this.elements.modelDropdown.innerHTML = this.models
            .map(model => `<div class="dropdown-option" data-model="${model}">${model}</div>`)
            .join('');
        
        // Add click handlers
        this.elements.modelDropdown.querySelectorAll('.dropdown-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const model = option.dataset.model;
                this.selectModel(model);
            });
        });
        
        // Auto-select first model if none is selected
        if (!this.currentModel && this.models.length > 0) {
            this.selectModel(this.models[0]);
        }
    }
    
    updateToolsList() {
        if (this.tools.length === 0) {
            this.elements.toolsList.innerHTML = '<div class="loading">No tools available</div>';
            return;
        }
        
        // Create tool descriptions
        const toolDescriptions = {
            'filesystem': 'File system operations: read, write, list directories, and manage files safely.',
            'calculator': 'Mathematical calculations: basic arithmetic, trigonometry, and expression evaluation.',
            'secure_tools': 'Advanced security-sensitive tools for authorized users only.'
        };
        
        this.elements.toolsList.innerHTML = this.tools
            .map(tool => `
                <div class="tool-item" data-tool="${tool}">
                    <h3>${tool.charAt(0).toUpperCase() + tool.slice(1)}</h3>
                    <p>${toolDescriptions[tool] || 'Tool for various operations and integrations.'}</p>
                </div>
            `).join('');
        
        // Add click handlers for tools
        this.elements.toolsList.querySelectorAll('.tool-item').forEach(item => {
            item.addEventListener('click', () => {
                const tool = item.dataset.tool;
                this.testTool(tool);
            });
        });
    }
    
    updateConnectionStatus(connected) {
        const statusText = this.elements.connectionStatus.querySelector('span');
        if (statusText) {
            statusText.textContent = connected ? 'Connected' : 'Disconnected';
        }
        this.elements.connectionStatus.className = `status ${connected ? 'connected' : 'disconnected'}`;
    }
    
    selectModel(model) {
        this.currentModel = model;
        this.elements.selectedModel.textContent = model;
        this.closeDropdown();
        this.updateSendButton();
    }
    
    toggleDropdown() {
        this.elements.modelDropdown.classList.toggle('hidden');
    }
    
    closeDropdown() {
        this.elements.modelDropdown.classList.add('hidden');
    }
    
    toggleToolsPanel() {
        this.elements.toolsPanel.classList.toggle('tools-panel-hidden');
    }
    
    closeToolsPanel() {
        this.elements.toolsPanel.classList.add('tools-panel-hidden');
    }
    
    autoResizeTextarea() {
        const textarea = this.elements.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
    }
    
    updateSendButton() {
        const hasMessage = this.elements.messageInput.value.trim().length > 0;
        const hasModel = this.currentModel && this.currentModel.length > 0;
        this.elements.sendButton.disabled = !hasMessage || !hasModel || !this.websocket || this.websocket.readyState !== WebSocket.OPEN;
    }
    
    sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message || !this.currentModel) return;
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Show thinking indicator
        const thinkingMessage = this.addMessage('assistant', '', true);
        
        // Send to backend
        this.websocket.send(JSON.stringify({
            type: 'chat',
            content: message,
            model: this.currentModel,
            user: this.user
        }));
        
        // Store thinking message for removal later
        this.currentThinkingMessage = thinkingMessage;
        
        // Clear input and reset height
        this.elements.messageInput.value = '';
        this.elements.messageInput.style.height = 'auto';
        this.updateSendButton();
    }
    
    testTool(toolName) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.showError('WebSocket not connected');
            return;
        }
        
        // Send MCP request
        this.websocket.send(JSON.stringify({
            type: 'mcp_request',
            server: toolName,
            request: {
                method: 'tools/list',
                params: {}
            },
            user: this.user
        }));
        
        this.addMessage('system', `Testing tool: ${toolName}`);
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'chat_response':
                // Remove thinking message if it exists
                if (this.currentThinkingMessage) {
                    this.currentThinkingMessage.remove();
                    this.currentThinkingMessage = null;
                }
                this.addMessage('assistant', data.message);
                break;
                
            case 'mcp_response':
                this.addMessage('assistant', `MCP Response from ${data.server}:\n${JSON.stringify(data.response, null, 2)}`);
                break;
                
            case 'error':
                // Remove thinking message if it exists
                if (this.currentThinkingMessage) {
                    this.currentThinkingMessage.remove();
                    this.currentThinkingMessage = null;
                }
                this.showError(data.message);
                break;
                
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    
    addMessage(sender, content, showThinking = false) {
        const messageContainer = this.elements.messages.querySelector('.message-container');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        // Create avatar
        const avatarDiv = document.createElement('div');
        avatarDiv.className = `message-avatar ${sender}-avatar`;
        avatarDiv.textContent = sender === 'user' ? 'Y' : 'A';
        
        // Create message bubble
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble ${sender}-bubble`;
        
        // Add author name
        const authorP = document.createElement('p');
        authorP.className = 'message-author';
        authorP.textContent = sender === 'user' ? 'You' : this.appName;
        
        // Add content
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (showThinking) {
            contentDiv.innerHTML = `
                <div class="thinking-indicator">
                    <svg class="spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Thinking...</span>
                </div>
            `;
        } else {
            // Process markdown for assistant messages, plain text for user messages
            if (sender === 'assistant' && typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
                const markdownHtml = marked.parse(content);
                const sanitizedHtml = DOMPurify.sanitize(markdownHtml);
                contentDiv.innerHTML = sanitizedHtml;
            } else {
                // For user messages or if markdown libraries aren't available, use plain text
                contentDiv.textContent = content;
            }
        }
        
        bubbleDiv.appendChild(authorP);
        bubbleDiv.appendChild(contentDiv);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(bubbleDiv);
        
        messageContainer.appendChild(messageDiv);
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        
        return messageDiv;
    }
    
    showError(message) {
        this.addMessage('system', `Error: ${message}`);
    }
    
    clearChat() {
        // Reset to welcome message
        const messageContainer = this.elements.messages.querySelector('.message-container');
        messageContainer.innerHTML = `
            <div class="message assistant">
                <div class="message-avatar assistant-avatar">A</div>
                <div class="message-bubble assistant-bubble">
                    <p class="message-author">${this.appName}</p>
                    <div class="message-content">
                        <p>Welcome to ${this.appName}! Select a model and start chatting. You can also explore available tools in the side panel.</p>
                    </div>
                </div>
            </div>
        `;
    }
}

// Global function for copying code blocks
function copyCodeBlock(button) {
    const codeBlock = button.parentElement.querySelector('code');
    const text = codeBlock.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        // Show success feedback
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        button.textContent = 'Copied!';
        button.classList.add('copied');
        setTimeout(() => {
            button.textContent = 'Copy';
            button.classList.remove('copied');
        }, 2000);
    });
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatUI();
});