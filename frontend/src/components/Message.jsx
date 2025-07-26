import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useChat } from '../contexts/ChatContext'
import { useState } from 'react'

// Configure marked with custom renderer for code blocks
const renderer = new marked.Renderer()
renderer.code = function(code, language) {
  const escapedCode = code.replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&#39;')
  
  return `<div class="code-block-container relative bg-gray-900 rounded-lg my-4">
    <pre class="p-4 overflow-x-auto"><code class="language-${language || 'text'} text-sm">${escapedCode}</code></pre>
    <button class="copy-button absolute top-2 right-2 bg-gray-700 hover:bg-gray-600 border border-gray-600 text-gray-200 px-2 py-1 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity" onclick="copyCodeBlock(this)" title="Copy code">Copy</button>
  </div>`
}

marked.setOptions({
  renderer: renderer,
  highlight: null,
  breaks: true,
  gfm: true
})

// Global function for copying code blocks
window.copyCodeBlock = (button) => {
  const codeBlock = button.parentElement.querySelector('code')
  const text = codeBlock.textContent
  
  navigator.clipboard.writeText(text).then(() => {
    const originalText = button.textContent
    button.textContent = 'Copied!'
    button.classList.add('bg-green-600', 'border-green-500')
    
    setTimeout(() => {
      button.textContent = originalText
      button.classList.remove('bg-green-600', 'border-green-500')
    }, 2000)
  }).catch(err => {
    console.error('Failed to copy text: ', err)
  })
}

const Message = ({ message }) => {
  const { appName } = useChat()
  
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  
  const avatarBg = isUser ? 'bg-green-600' : isSystem ? 'bg-yellow-600' : 'bg-blue-600'
  const avatarText = isUser ? 'Y' : isSystem ? 'S' : 'A'
  const authorName = isUser ? 'You' : isSystem ? 'System' : appName
  
  const renderContent = () => {
    if (isUser || isSystem) {
      return <div className="text-gray-200">{message.content}</div>
    }
    
    // Render markdown for assistant messages
    // Ensure content is a string before parsing
    const content = typeof message.content === 'string' ? message.content : String(message.content || '')
    const markdownHtml = marked.parse(content)
    const sanitizedHtml = DOMPurify.sanitize(markdownHtml)
    
    return (
      <div 
        className="text-gray-200 prose prose-invert max-w-none group"
        dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
      />
    )
  }

  return (
    <div className={`flex items-start gap-3 max-w-4xl mx-auto ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full ${avatarBg} flex items-center justify-center text-white text-sm font-medium flex-shrink-0`}>
        {avatarText}
      </div>
      
      {/* Message Content */}
      <div className={`max-w-[70%] ${isUser ? 'bg-blue-600' : 'bg-gray-800'} rounded-lg p-4`}>
        <div className="text-sm font-medium text-gray-300 mb-2">
          {authorName}
        </div>
        {renderContent()}
      </div>
    </div>
  )
}

export default Message