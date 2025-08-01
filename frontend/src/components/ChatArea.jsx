import { useState, useRef, useEffect } from 'react'
import { useChat } from '../contexts/ChatContext'
import { useWS } from '../contexts/WSContext'
import { Send, Paperclip, X } from 'lucide-react'
import Message from './Message'
import WelcomeScreen from './WelcomeScreen'

const ChatArea = ({ canvasPanelOpen, canvasPanelWidth }) => {
  const [inputValue, setInputValue] = useState('')
  const [isMobile, setIsMobile] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState({})
  const [showToolAutocomplete, setShowToolAutocomplete] = useState(false)
  const [filteredTools, setFilteredTools] = useState([])
  const [selectedToolIndex, setSelectedToolIndex] = useState(0)
  const textareaRef = useRef(null)
  const messagesRef = useRef(null)
  const fileInputRef = useRef(null)
  
  const { 
    messages, 
    isWelcomeVisible, 
    isThinking, 
    sendChatMessage, 
    currentModel,
    tools,
    selectedTools,
    toggleTool,
    toolChoiceRequired,
    setToolChoiceRequired
  } = useChat()
  const { isConnected } = useWS()

  // Auto-resize textarea
  const autoResizeTextarea = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px'
    }
  }

  // Check for mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Focus message input on page load
  useEffect(() => {
    const focusInput = () => {
      if (textareaRef.current && !isMobile) { // Don't auto-focus on mobile to prevent keyboard popup
        textareaRef.current.focus()
      }
    }
    
    // Focus after a brief delay to ensure the component is fully rendered
    const timeoutId = setTimeout(focusInput, 200)
    return () => clearTimeout(timeoutId)
  }, [isMobile])

  // Scroll to bottom when messages change - debounced for performance
  useEffect(() => {
    if (messagesRef.current) {
      const timeoutId = setTimeout(() => {
        requestAnimationFrame(() => {
          if (messagesRef.current) {
            messagesRef.current.scrollTop = messagesRef.current.scrollHeight
          }
        })
      }, 100)
      
      return () => clearTimeout(timeoutId)
    }
  }, [messages, isThinking])

  const handleSubmit = (e) => {
    e.preventDefault()
    const message = inputValue.trim()
    if (!message || !currentModel || !isConnected) return
    
    sendChatMessage(message, uploadedFiles)
    setInputValue('')
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    // Handle autocomplete navigation
    if (showToolAutocomplete) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedToolIndex(prev => 
          prev < filteredTools.length - 1 ? prev + 1 : 0
        )
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedToolIndex(prev => 
          prev > 0 ? prev - 1 : filteredTools.length - 1
        )
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        if (filteredTools[selectedToolIndex]) {
          selectTool(filteredTools[selectedToolIndex])
        }
        return
      } else if (e.key === 'Escape') {
        e.preventDefault()
        setShowToolAutocomplete(false)
        return
      }
    }
    
    // Normal enter handling
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInputChange = (e) => {
    const value = e.target.value
    setInputValue(value)
    autoResizeTextarea()
    
    // Handle slash command autocomplete
    handleSlashCommand(value)
  }

  // Get all available tools as flat list
  const getAllAvailableTools = () => {
    const allTools = []
    tools.forEach(toolServer => {
      toolServer.tools.forEach(toolName => {
        allTools.push({
          key: `${toolServer.server}_${toolName}`,
          name: toolName,
          server: toolServer.server,
          description: toolServer.description
        })
      })
    })
    return allTools
  }

  // Handle slash command logic
  const handleSlashCommand = (value) => {
    if (value.startsWith('/')) {
      // Extract the command part (before any space)
      const spaceIndex = value.indexOf(' ')
      const commandPart = spaceIndex === -1 ? value.slice(1) : value.slice(1, spaceIndex)
      const query = commandPart.toLowerCase()
      const availableTools = getAllAvailableTools()
      
      // Only show autocomplete if we're still typing the command (no space yet or at the end)
      const showAutocomplete = spaceIndex === -1 || value.length === spaceIndex + 1
      
      if (showAutocomplete) {
        if (query === '') {
          // Show all tools when just "/" is typed
          setFilteredTools(availableTools)
          setShowToolAutocomplete(true)
          setSelectedToolIndex(0)
        } else {
          // Filter tools based on query
          const filtered = availableTools.filter(tool => 
            tool.name.toLowerCase().includes(query) ||
            tool.server.toLowerCase().includes(query)
          )
          
          if (filtered.length > 0) {
            setFilteredTools(filtered)
            setShowToolAutocomplete(true)
            setSelectedToolIndex(0)
          } else {
            setShowToolAutocomplete(false)
          }
        }
      } else {
        setShowToolAutocomplete(false)
      }
    } else {
      setShowToolAutocomplete(false)
    }
  }

  // Check if input contains a slash command
  const hasSlashCommand = inputValue.startsWith('/') && inputValue.includes(' ')

  // Handle tool selection from autocomplete
  const selectTool = (tool) => {
    // Enable the tool if not already selected
    if (!selectedTools.has(tool.key)) {
      toggleTool(tool.key)
    }
    
    // Enable required tool call
    setToolChoiceRequired(true)
    
    // Replace the slash command with the tool name and add a space
    setInputValue(`/${tool.name} `)
    setShowToolAutocomplete(false)
    
    // Focus back to textarea
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files)
    files.forEach(file => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const base64Data = e.target.result.split(',')[1] // Remove data URL prefix
        setUploadedFiles(prev => ({
          ...prev,
          [file.name]: base64Data
        }))
      }
      reader.readAsDataURL(file)
    })
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (filename) => {
    setUploadedFiles(prev => {
      const newFiles = { ...prev }
      delete newFiles[filename]
      return newFiles
    })
  }

  const triggerFileUpload = () => {
    fileInputRef.current?.click()
  }

  const canSend = inputValue.trim().length > 0 && currentModel && isConnected

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
      {/* Welcome Screen */}
      {isWelcomeVisible && <WelcomeScreen />}

      {/* Messages */}
      <main 
        ref={messagesRef}
        className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4 min-h-0"
        style={{ 
          paddingRight: canvasPanelOpen && !isMobile ? `${canvasPanelWidth + 16}px` : '1rem',
          transition: 'padding-right 150ms ease-out'
        }}
      >
        {messages.map((message, index) => (
          <Message key={`${index}-${message.role}-${message.content?.substring(0, 20)}`} message={message} />
        ))}
        
        {/* Thinking indicator */}
        {isThinking && (
          <div className="flex items-start gap-3 max-w-4xl mx-auto">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
              A
            </div>
            <div className="max-w-[70%] bg-gray-800 rounded-lg p-4">
              <div className="text-sm font-medium text-gray-300 mb-2">
                Chat UI
              </div>
              <div className="flex items-center gap-2 text-gray-400">
                <svg className="w-4 h-4 spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Input Area */}
      <footer 
        className="p-4 border-t border-gray-700 flex-shrink-0"
        style={{ 
          paddingRight: canvasPanelOpen && !isMobile ? `${canvasPanelWidth + 16}px` : '1rem',
          transition: 'padding-right 150ms ease-out'
        }}
      >
        <div className="max-w-4xl mx-auto">
          {/* Uploaded Files Display */}
          {Object.keys(uploadedFiles).length > 0 && (
            <div className="mb-3 p-3 bg-gray-800 rounded-lg border border-gray-600">
              <div className="text-sm text-gray-300 mb-2">Uploaded Files:</div>
              <div className="flex flex-wrap gap-2">
                {Object.keys(uploadedFiles).map(filename => (
                  <div key={filename} className="flex items-center gap-2 bg-gray-700 px-3 py-1 rounded-full text-sm">
                    <span className="text-gray-200">{filename}</span>
                    <button
                      onClick={() => removeFile(filename)}
                      className="text-gray-400 hover:text-red-400 transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="flex gap-3">
            <button
              type="button"
              onClick={triggerFileUpload}
              className="px-3 py-3 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg flex items-center justify-center transition-colors flex-shrink-0"
              title="Upload files"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Type your message..."
                rows={1}
                className={`w-full px-4 py-3 bg-gray-800 rounded-lg text-gray-200 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:border-transparent ${
                  hasSlashCommand 
                    ? 'border-2 border-yellow-500 focus:ring-yellow-500 bg-yellow-900/10' 
                    : 'border border-gray-600 focus:ring-blue-500'
                }`}
                style={{ minHeight: '48px', maxHeight: '128px' }}
              />
              
              {/* Tool Autocomplete Dropdown */}
              {showToolAutocomplete && filteredTools.length > 0 && (
                <div className="absolute bottom-full left-0 right-0 mb-2 bg-gray-800 border border-gray-600 rounded-lg shadow-lg max-h-64 overflow-y-auto z-50">
                  <div className="p-2 text-xs text-gray-400 bg-gray-700 border-b border-gray-600">
                    Use ↑↓ to navigate, Enter to select, Esc to cancel
                  </div>
                  {filteredTools.map((tool, index) => (
                    <div
                      key={tool.key}
                      onClick={() => selectTool(tool)}
                      className={`px-3 py-2 cursor-pointer transition-colors border-b border-gray-700 last:border-b-0 ${
                        index === selectedToolIndex 
                          ? 'bg-blue-600 text-white' 
                          : 'hover:bg-gray-700 text-gray-200'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-black text-white">/{tool.name}</span>
                        <span className="text-xs text-gray-400">from {tool.server}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <button
              type="submit"
              disabled={!canSend}
              className={`px-4 py-3 rounded-lg flex items-center justify-center transition-colors flex-shrink-0 ${
                canSend 
                  ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                  : 'bg-gray-700 text-gray-400 cursor-not-allowed'
              }`}
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
          
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileUpload}
            className="hidden"
            accept=".pdf,.txt,.doc,.docx,.jpg,.jpeg,.png,.gif,.csv,.xlsx,.xls,.json,.md,.log"
          />
          
          <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
            <span>Press Shift + Enter for new line</span>
            {Object.keys(uploadedFiles).length > 0 && (
              <span>{Object.keys(uploadedFiles).length} file(s) uploaded</span>
            )}
          </div>
        </div>
      </footer>
    </div>
  )
}

export default ChatArea