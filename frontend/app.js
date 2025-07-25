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
        this.selectedTools = new Set(); // Track selected tools
        this.dataSources = [];
        this.selectedDataSources = new Set(); // Track selected data sources
        this.onlyRag = true; // Default to true as per instructions
        this.agentModeEnabled = false; // Agent mode state
        this.agentMaxSteps = 5; // Default max steps
        this.currentAgentStep = 0; // Current step counter
        this.agentModeAvailable = true; // Whether agent mode UI is available
        this.isWelcomeScreenVisible = true; // Track welcome screen visibility
        
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
            appTitle: document.querySelector('.header-title'),
            userEmail: document.getElementById('user-email'),
            toolsList: document.getElementById('tools-list'),
            connectionStatus: document.getElementById('connection-status'),
            messages: document.getElementById('messages'),
            messageInput: document.getElementById('message-input'),
            sendButton: document.getElementById('send-button'),
            
            // Welcome screen elements
            welcomeScreen: document.getElementById('welcome-screen'),
            welcomeAppTitle: document.getElementById('welcome-app-title'),
            
            // Dropdown elements
            modelButton: document.getElementById('model-button'),
            modelDropdown: document.getElementById('model-dropdown'),
            selectedModel: document.getElementById('selected-model'),
            
            // Tools panel elements
            toggleToolsPanel: document.getElementById('toggle-tools-panel'),
            closeToolsPanel: document.getElementById('close-tools-panel'),
            toolsPanel: document.getElementById('tools-panel'),
            
            // RAG panel elements
            toggleRagPanel: document.getElementById('toggle-rag-panel'),
            closeRagPanel: document.getElementById('close-rag-panel'),
            ragPanel: document.getElementById('rag-panel'),
            onlyRagCheckbox: document.getElementById('only-rag'),
            dataSourcesList: document.getElementById('data-sources-list'),
            
            // Agent mode elements
            toggleAgentModal: document.getElementById('toggle-agent-modal'),
            agentModal: document.getElementById('agent-modal'),
            agentModalBackdrop: document.getElementById('agent-modal-backdrop'),
            closeAgentModal: document.getElementById('close-agent-modal'),
            agentModeCheckbox: document.getElementById('agent-mode'),
            agentStatus: document.getElementById('agent-status'),
            agentStepsSlider: document.getElementById('agent-steps-slider'),
            agentStepsValue: document.getElementById('agent-steps-value'),
            agentProgress: document.getElementById('agent-progress'),
            
            // Canvas panel elements
            canvasPanel: document.getElementById('canvas-panel'),
            canvasContent: document.getElementById('canvas-content'),
            closeCanvasPanel: document.getElementById('close-canvas-panel'),
            chatContainer: document.getElementById('chat-container'),
            currentStep: document.getElementById('current-step'),
            maxSteps: document.getElementById('max-steps'),
            progressFill: document.getElementById('progress-fill')
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
        
        // RAG panel functionality
        this.elements.toggleRagPanel.addEventListener('click', () => this.toggleRagPanel());
        this.elements.closeRagPanel.addEventListener('click', () => this.closeRagPanel());
        this.elements.onlyRagCheckbox.addEventListener('change', (e) => {
            this.onlyRag = e.target.checked;
        });
        
        // Agent modal functionality
        this.elements.toggleAgentModal.addEventListener('click', () => this.toggleAgentModal());
        this.elements.closeAgentModal.addEventListener('click', () => this.closeAgentModal());
        this.elements.agentModalBackdrop.addEventListener('click', () => this.closeAgentModal());
        
        // Agent mode functionality
        this.elements.agentModeCheckbox.addEventListener('change', (e) => {
            this.agentModeEnabled = e.target.checked;
            this.updateAgentStatus();
        });
        
        this.elements.agentStepsSlider.addEventListener('input', (e) => {
            this.agentMaxSteps = parseInt(e.target.value);
            this.elements.agentStepsValue.textContent = this.agentMaxSteps;
        });
        
        // Canvas panel functionality
        this.elements.closeCanvasPanel.addEventListener('click', () => this.closeCanvasPanel());
        
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
            this.dataSources = config.data_sources || [];
            this.user = config.user || 'Unknown';
            this.agentModeAvailable = config.agent_mode_available !== false; // Default to true if not specified
            
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
        
        // Update data sources list
        this.updateDataSourcesList();
        
        // Show/hide agent mode button based on availability
        this.updateAgentModeVisibility();
    }
    
    updateWelcomeMessage() {
        // Update the welcome screen app title
        if (this.elements.welcomeAppTitle) {
            this.elements.welcomeAppTitle.textContent = this.appName;
        }
    }
    
    showWelcomeScreen() {
        if (this.elements.welcomeScreen) {
            this.elements.welcomeScreen.classList.remove('hidden');
            this.isWelcomeScreenVisible = true;
        }
    }
    
    hideWelcomeScreen() {
        if (this.elements.welcomeScreen) {
            this.elements.welcomeScreen.classList.add('hidden');
            this.isWelcomeScreenVisible = false;
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
        
        // Auto-select canvas tool by default
        const canvasTool = this.tools.find(tool => tool.server === 'canvas');
        if (canvasTool && canvasTool.tools.includes('canvas')) {
            this.selectedTools.add('canvas_canvas');
        }
        
        this.elements.toolsList.innerHTML = this.tools
            .map(toolServer => `
                <div class="tool-server" data-server="${toolServer.server}">
                    <div class="tool-server-header">
                        <h3>${toolServer.server.charAt(0).toUpperCase() + toolServer.server.slice(1)}</h3>
                        <span class="tool-count">${toolServer.tool_count} tools</span>
                        ${toolServer.is_exclusive ? '<span class="exclusive-badge">Exclusive</span>' : ''}
                        <button class="select-server-btn" data-server="${toolServer.server}">
                            Select All
                        </button>
                    </div>
                    <p class="tool-server-description">${toolServer.description}</p>
                    <div class="tool-list">
                        ${toolServer.tools.map(tool => {
                            const toolKey = `${toolServer.server}_${tool}`;
                            const isSelected = this.selectedTools.has(toolKey);
                            return `
                                <span class="tool-tag ${isSelected ? 'selected' : ''}" 
                                      data-server="${toolServer.server}" 
                                      data-tool="${tool}"
                                      data-tool-key="${toolKey}">
                                    ${tool}
                                </span>
                            `;
                        }).join('')}
                    </div>
                </div>
            `).join('');
        
        // Add click handlers for server selection buttons
        this.elements.toolsList.querySelectorAll('.select-server-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const server = btn.dataset.server;
                this.toggleServerTools(server);
            });
        });
        
        // Add click handlers for individual tool selection
        this.elements.toolsList.querySelectorAll('.tool-tag').forEach(tag => {
            tag.addEventListener('click', () => {
                const toolKey = tag.dataset.toolKey;
                this.toggleTool(toolKey, tag);
            });
        });
    }
    
    toggleServerTools(serverName) {
        const serverTools = this.tools.find(t => t.server === serverName);
        if (!serverTools) return;
        
        const serverToolKeys = serverTools.tools.map(tool => `${serverName}_${tool}`);
        const allSelected = serverToolKeys.every(key => this.selectedTools.has(key));
        
        if (allSelected) {
            // Deselect all tools from this server
            serverToolKeys.forEach(key => this.selectedTools.delete(key));
        } else {
            // Select all tools from this server
            serverToolKeys.forEach(key => this.selectedTools.add(key));
        }
        
        // Update the display
        this.updateToolsList();
        this.updateSelectedToolsDisplay();
    }
    
    toggleTool(toolKey, tagElement) {
        if (this.selectedTools.has(toolKey)) {
            this.selectedTools.delete(toolKey);
            tagElement.classList.remove('selected');
        } else {
            this.selectedTools.add(toolKey);
            tagElement.classList.add('selected');
        }
        
        this.updateSelectedToolsDisplay();
    }
    
    updateSelectedToolsDisplay() {
        // Update button text based on selection
        this.elements.toolsList.querySelectorAll('.select-server-btn').forEach(btn => {
            const server = btn.dataset.server;
            const serverTools = this.tools.find(t => t.server === server);
            if (!serverTools) return;
            
            const serverToolKeys = serverTools.tools.map(tool => `${server}_${tool}`);
            const selectedCount = serverToolKeys.filter(key => this.selectedTools.has(key)).length;
            
            if (selectedCount === 0) {
                btn.textContent = 'Select All';
                btn.classList.remove('selected');
            } else if (selectedCount === serverToolKeys.length) {
                btn.textContent = 'Deselect All';
                btn.classList.add('selected');
            } else {
                btn.textContent = `Select All (${selectedCount}/${serverToolKeys.length})`;
                btn.classList.remove('selected');
            }
        });
    }
    
    updateDataSourcesList() {
        if (this.dataSources.length === 0) {
            this.elements.dataSourcesList.innerHTML = '<div class="loading">No data sources available</div>';
            return;
        }
        
        this.elements.dataSourcesList.innerHTML = this.dataSources
            .map(dataSource => {
                const isSelected = this.selectedDataSources.has(dataSource);
                return `
                    <div class="data-source-item ${isSelected ? 'selected' : ''}" 
                         data-source="${dataSource}">
                        <div class="data-source-name">${dataSource.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                        <div class="data-source-description">Click to ${isSelected ? 'deselect' : 'select'} this data source</div>
                    </div>
                `;
            }).join('');
        
        // Add click handlers for data source selection
        this.elements.dataSourcesList.querySelectorAll('.data-source-item').forEach(item => {
            item.addEventListener('click', () => {
                const dataSource = item.dataset.source;
                this.toggleDataSource(dataSource, item);
            });
        });
    }
    
    toggleDataSource(dataSource, itemElement) {
        if (this.selectedDataSources.has(dataSource)) {
            this.selectedDataSources.delete(dataSource);
            itemElement.classList.remove('selected');
            itemElement.querySelector('.data-source-description').textContent = 'Click to select this data source';
        } else {
            this.selectedDataSources.add(dataSource);
            itemElement.classList.add('selected');
            itemElement.querySelector('.data-source-description').textContent = 'Click to deselect this data source';
        }
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
    
    toggleRagPanel() {
        this.elements.ragPanel.classList.toggle('rag-panel-hidden');
    }
    
    closeRagPanel() {
        this.elements.ragPanel.classList.add('rag-panel-hidden');
    }
    
    showCanvasPanel() {
        this.elements.canvasPanel.classList.remove('canvas-panel-hidden');
        this.elements.canvasPanel.classList.add('canvas-panel-visible');
        // Adjust chat container width when canvas is shown
        this.elements.chatContainer.style.width = '50%';
        // Ensure messages scroll properly after layout change
        setTimeout(() => this.scrollToBottom(), 200);
    }
    
    closeCanvasPanel() {
        this.elements.canvasPanel.classList.remove('canvas-panel-visible');
        this.elements.canvasPanel.classList.add('canvas-panel-hidden');
        // Reset chat container width when canvas is hidden
        this.elements.chatContainer.style.width = '100%';
        // Ensure messages scroll properly after layout change
        setTimeout(() => this.scrollToBottom(), 200);
    }
    
    updateCanvasContent(content) {
        // Clear placeholder and render markdown content
        this.elements.canvasContent.innerHTML = '';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'markdown-content';
        
        if (typeof marked !== 'undefined') {
            // Sanitize the content using DOMPurify if available
            let htmlContent = marked.parse(content);
            if (typeof DOMPurify !== 'undefined') {
                htmlContent = DOMPurify.sanitize(htmlContent);
            }
            contentDiv.innerHTML = htmlContent;
        } else {
            // Fallback to plain text if marked is not available
            contentDiv.textContent = content;
        }
        
        this.elements.canvasContent.appendChild(contentDiv);
        
        // Show canvas panel if it's hidden
        if (this.elements.canvasPanel.classList.contains('canvas-panel-hidden')) {
            this.showCanvasPanel();
        }
    }
    
    toggleAgentModal() {
        this.elements.agentModal.classList.toggle('hidden');
    }
    
    closeAgentModal() {
        this.elements.agentModal.classList.add('hidden');
    }
    
    updateAgentModeVisibility() {
        const agentButton = this.elements.toggleAgentModal;
        if (this.agentModeAvailable) {
            agentButton.style.display = '';
        } else {
            agentButton.style.display = 'none';
            // Also close modal if it's open
            this.closeAgentModal();
        }
    }
    
    updateAgentStatus() {
        const statusElement = this.elements.agentStatus;
        if (this.agentModeEnabled) {
            statusElement.textContent = 'Enabled';
            statusElement.style.color = '#60a5fa';
        } else {
            statusElement.textContent = 'Disabled';
            statusElement.style.color = '#9ca3af';
        }
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
    
    scrollToBottom() {
        const messagesContainer = this.elements.messages;
        if (messagesContainer) {
            // Use requestAnimationFrame to ensure DOM has been updated
            requestAnimationFrame(() => {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            });
        }
    }
    
    sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message || !this.currentModel) return;
        
        // Hide welcome screen when first message is sent
        if (this.isWelcomeScreenVisible) {
            this.hideWelcomeScreen();
        }
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Show thinking indicator
        const thinkingMessage = this.addMessage('assistant', '', true);
        
        // Prepare selected tools and data sources for backend
        const selectedToolsList = Array.from(this.selectedTools);
        const selectedDataSourcesList = Array.from(this.selectedDataSources);
        
        // Send to backend with selected tools, RAG parameters, and agent mode (if available)
        const payload = {
            type: 'chat',
            content: message,
            model: this.currentModel,
            selected_tools: selectedToolsList,
            selected_data_sources: selectedDataSourcesList,
            only_rag: this.onlyRag,
            user: this.user
        };
        
        // Only include agent mode parameters if agent mode is available
        if (this.agentModeAvailable) {
            payload.agent_mode = this.agentModeEnabled;
            payload.agent_max_steps = this.agentMaxSteps;
        }
        
        this.websocket.send(JSON.stringify(payload));
        
        // Store thinking message for removal later
        this.currentThinkingMessage = thinkingMessage;
        
        // Clear input and reset height
        this.elements.messageInput.value = '';
        this.elements.messageInput.style.height = 'auto';
        this.updateSendButton();
    }
    
    testTool(serverName, toolName) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.showError('WebSocket not connected');
            return;
        }
        
        // Send MCP request to test a specific tool
        this.websocket.send(JSON.stringify({
            type: 'mcp_request',
            server: serverName,
            tool_name: toolName,
            arguments: this.getTestArguments(toolName),
            user: this.user
        }));
        
        this.addMessage('assistant', `Testing ${toolName} from ${serverName} server...`);
    }
    
    getTestArguments(toolName) {
        // Provide sample test arguments for different tools
        const testArgs = {
            'add': { a: 5, b: 3 },
            'subtract': { a: 10, b: 4 },
            'multiply': { a: 6, b: 7 },
            'divide': { a: 15, b: 3 },
            'sqrt': { number: 16 },
            'list_directory': { path: '.' },
            'file_exists': { path: 'README.md' },
            'evaluate': { expression: '2 + 2 * 3' }
        };
        
        return testArgs[toolName] || {};
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
                
            case 'intermediate_update':
                this.handleIntermediateUpdate(data);
                break;
                
            case 'agent_step_update':
                this.handleAgentStepUpdate(data);
                break;
                
            case 'agent_final_response':
                this.handleAgentFinalResponse(data);
                break;
                
            case 'canvas_content':
                this.handleCanvasContent(data);
                break;
                
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    
    handleIntermediateUpdate(data) {
        const updateType = data.update_type;
        const updateData = data.data;
        
        switch (updateType) {
            case 'tool_call':
                this.addToolCallUpdate(updateData);
                break;
            case 'tool_result':
                this.addToolResultUpdate(updateData);
                break;
            case 'canvas_content':
                this.handleCanvasContent(updateData);
                break;
            default:
                console.warn('Unknown intermediate update type:', updateType);
        }
    }
    
    addToolCallUpdate(data) {
        const messageContainer = this.elements.messages.querySelector('.message-container');
        
        const updateDiv = document.createElement('div');
        updateDiv.className = 'intermediate-update tool-call-update';
        updateDiv.dataset.toolCallId = data.tool_call_id;
        
        const content = `
            <div class="tool-update-header">
                <span class="tool-info">Calling tool: <strong>${data.tool_name}</strong> (${data.server_name})</span>
                <span class="tool-status calling">Executing...</span>
            </div>
            <div class="tool-parameters">
                <details>
                    <summary>Parameters</summary>
                    <pre><code>${JSON.stringify(data.parameters, null, 2)}</code></pre>
                </details>
            </div>
        `;
        
        updateDiv.innerHTML = content;
        messageContainer.appendChild(updateDiv);
        this.scrollToBottom();
    }
    
    addToolResultUpdate(data) {
        // Find the corresponding tool call update
        const messageContainer = this.elements.messages.querySelector('.message-container');
        const toolCallUpdate = messageContainer.querySelector(`[data-tool-call-id="${data.tool_call_id}"]`);
        
        if (toolCallUpdate) {
            // Update the existing tool call to show result
            const statusElement = toolCallUpdate.querySelector('.tool-status');
            const parametersDiv = toolCallUpdate.querySelector('.tool-parameters');
            
            if (data.success) {
                statusElement.textContent = 'Completed';
                statusElement.className = 'tool-status completed';
            } else {
                statusElement.textContent = 'Failed';
                statusElement.className = 'tool-status failed';
            }
            
            // Add result section
            const resultDiv = document.createElement('div');
            resultDiv.className = 'tool-result';
            
            const resultContent = data.success 
                ? `<details>
                     <summary>Result</summary>
                     <pre><code>${data.result}</code></pre>
                   </details>`
                : `<details open>
                     <summary>Error</summary>
                     <pre class="error"><code>${data.result}</code></pre>
                   </details>`;
            
            resultDiv.innerHTML = resultContent;
            parametersDiv.after(resultDiv);
        } else {
            // Fallback: create a standalone result update
            const updateDiv = document.createElement('div');
            updateDiv.className = 'intermediate-update tool-result-update';
            
            const status = data.success ? 'completed' : 'failed';
            
            const content = `
                <div class="tool-update-header">
                    <span class="tool-info">Tool result: <strong>${data.tool_name}</strong></span>
                    <span class="tool-status ${status}">${data.success ? 'Completed' : 'Failed'}</span>
                </div>
                <div class="tool-result">
                    <details ${data.success ? '' : 'open'}>
                        <summary>Result</summary>
                        <pre class="${data.success ? '' : 'error'}"><code>${data.result}</code></pre>
                    </details>
                </div>
            `;
            
            updateDiv.innerHTML = content;
            messageContainer.appendChild(updateDiv);
        }
        
        this.scrollToBottom();
    }
    
    handleAgentStepUpdate(data) {
        this.currentAgentStep = data.current_step;
        const maxSteps = data.max_steps;
        
        // Only update progress if modal is currently open
        if (!this.elements.agentModal.classList.contains('hidden')) {
            this.elements.agentProgress.classList.remove('hidden');
            this.elements.currentStep.textContent = this.currentAgentStep;
            this.elements.maxSteps.textContent = maxSteps;
            
            // Update progress bar
            const progressPercent = (this.currentAgentStep / maxSteps) * 100;
            this.elements.progressFill.style.width = `${progressPercent}%`;
        }
        
        console.log(`Agent step ${this.currentAgentStep}/${maxSteps}`);
    }
    
    handleAgentFinalResponse(data) {
        // Remove thinking message if it exists
        if (this.currentThinkingMessage) {
            this.currentThinkingMessage.remove();
            this.currentThinkingMessage = null;
        }
        
        // Hide agent progress (only if modal is open)
        if (!this.elements.agentModal.classList.contains('hidden')) {
            this.elements.agentProgress.classList.add('hidden');
        }
        this.currentAgentStep = 0;
        
        // Add final response with step summary
        const responseWithSummary = `${data.message}\n\n*Agent completed in ${data.steps_taken} steps*`;
        this.addMessage('assistant', responseWithSummary);
    }
    
    handleCanvasContent(data) {
        console.log('Canvas content received:', data);
        if (data.content) {
            this.updateCanvasContent(data.content);
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
        
        // Scroll to bottom after adding message
        setTimeout(() => this.scrollToBottom(), 100);
        
        return messageDiv;
    }
    
    showError(message) {
        this.addMessage('system', `Error: ${message}`);
    }
    
    clearChat() {
        // Clear message container and show welcome screen
        const messageContainer = this.elements.messages.querySelector('.message-container');
        messageContainer.innerHTML = '';
        this.showWelcomeScreen();
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