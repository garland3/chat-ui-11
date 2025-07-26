import { useState, useRef, useEffect } from 'react'
import { useChat } from '../contexts/ChatContext'
import { useWS } from '../contexts/WSContext'
import { Send } from 'lucide-react'
import Message from './Message'
import WelcomeScreen from './WelcomeScreen'

const ChatArea = ({ canvasPanelOpen }) => {
  const [inputValue, setInputValue] = useState('')
  const [isMobile, setIsMobile] = useState(false)
  const textareaRef = useRef(null)
  const messagesRef = useRef(null)
  
  const { 
    messages, 
    isWelcomeVisible, 
    isThinking, 
    sendChatMessage, 
    currentModel 
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
    
    sendChatMessage(message)
    setInputValue('')
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInputChange = (e) => {
    setInputValue(e.target.value)
    autoResizeTextarea()
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
          paddingRight: canvasPanelOpen && !isMobile ? 'calc(50vw + 1rem)' : '1rem',
          transition: 'padding-right 300ms ease-in-out'
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
          paddingRight: canvasPanelOpen && !isMobile ? 'calc(50vw + 1rem)' : '1rem',
          transition: 'padding-right 300ms ease-in-out'
        }}
      >
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Type your message..."
                rows={1}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-gray-200 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                style={{ minHeight: '48px', maxHeight: '128px' }}
              />
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
          
          <div className="flex items-center justify-between mt-2 text-xs text-gray-400">
            <span>Press Shift + Enter for new line</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default ChatArea