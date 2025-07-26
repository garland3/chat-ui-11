import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useChat } from '../contexts/ChatContext'
import { useState, memo, useEffect } from 'react'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

// Register common languages for better syntax highlighting
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import rust from 'highlight.js/lib/languages/rust'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import cpp from 'highlight.js/lib/languages/cpp'
import css from 'highlight.js/lib/languages/css'
import html from 'highlight.js/lib/languages/xml'
import json from 'highlight.js/lib/languages/json'
import yaml from 'highlight.js/lib/languages/yaml'
import sql from 'highlight.js/lib/languages/sql'
import bash from 'highlight.js/lib/languages/bash'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('rust', rust)
hljs.registerLanguage('rs', rust)
hljs.registerLanguage('go', go)
hljs.registerLanguage('golang', go)
hljs.registerLanguage('java', java)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('c++', cpp)
hljs.registerLanguage('css', css)
hljs.registerLanguage('html', html)
hljs.registerLanguage('xml', html)
hljs.registerLanguage('json', json)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('shell', bash)
hljs.registerLanguage('sh', bash)

// Configure marked with custom renderer for code blocks
const renderer = new marked.Renderer()
renderer.code = function(code, language) {
  // Handle different code input types
  let codeString = ''
  let actualLanguage = language
  
  if (typeof code === 'string') {
    codeString = code
  } else if (code && typeof code === 'object') {
    // Check if this is a structured code block object
    if (code.text && typeof code.text === 'string') {
      // Use the text property for structured code blocks
      codeString = code.text
      // Use the lang property if available
      if (code.lang && !actualLanguage) {
        actualLanguage = code.lang
      }
    } else if (code.raw && typeof code.raw === 'string') {
      // Handle raw markdown code blocks - extract the content
      const rawMatch = code.raw.match(/```(\w*)\n([\s\S]*?)\n```/)
      if (rawMatch) {
        codeString = rawMatch[2] || ''
        if (rawMatch[1] && !actualLanguage) {
          actualLanguage = rawMatch[1]
        }
      } else {
        codeString = code.raw
      }
    } else {
      // Fallback to JSON for other objects
      try {
        codeString = JSON.stringify(code, null, 2)
        actualLanguage = 'json'
      } catch (e) {
        codeString = String(code || '')
      }
    }
  } else {
    codeString = String(code || '')
  }
  
  // Apply syntax highlighting
  let highlightedCode = ''
  if (actualLanguage && hljs.getLanguage(actualLanguage)) {
    try {
      const result = hljs.highlight(codeString, { language: actualLanguage })
      highlightedCode = result.value
    } catch (e) {
      console.warn('Highlight.js error for language', actualLanguage, e)
      // Fallback to manual escaping
      highlightedCode = codeString.replace(/&/g, '&amp;')
                          .replace(/</g, '&lt;')
                          .replace(/>/g, '&gt;')
                          .replace(/"/g, '&quot;')
                          .replace(/'/g, '&#39;')
    }
  } else {
    // Auto-detect language if not specified or not supported
    try {
      const result = hljs.highlightAuto(codeString)
      highlightedCode = result.value
      // Update language for display
      if (result.language && !actualLanguage) {
        actualLanguage = result.language
      }
    } catch (e) {
      console.warn('Highlight.js auto-detection error', e)
      // Fallback to manual escaping
      highlightedCode = codeString.replace(/&/g, '&amp;')
                          .replace(/</g, '&lt;')
                          .replace(/>/g, '&gt;')
                          .replace(/"/g, '&quot;')
                          .replace(/'/g, '&#39;')
    }
  }
  
  return `<div class="code-block-container relative bg-gray-900 rounded-lg my-4 border border-gray-700">
    <div class="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
      <span class="text-xs text-gray-400 font-medium uppercase tracking-wider">${actualLanguage || 'text'}</span>
      <button 
        class="copy-button bg-gray-700 hover:bg-gray-600 border border-gray-600 text-gray-200 px-3 py-1 rounded text-xs transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500" 
        data-action="copy-code"
        title="Copy code to clipboard"
        type="button"
      >Copy</button>
    </div>
    <pre class="p-4 overflow-x-auto bg-gray-900 m-0"><code class="hljs language-${actualLanguage || 'text'} text-sm leading-relaxed">${highlightedCode}</code></pre>
  </div>`
}

marked.setOptions({
  renderer: renderer,
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.warn('Highlight.js error:', err)
      }
    }
    try {
      return hljs.highlightAuto(code).value
    } catch (err) {
      console.warn('Highlight.js auto-detection error:', err)
      return code
    }
  },
  breaks: true,
  gfm: true
})

// Copy function for code blocks
const copyCodeBlock = (button) => {
  try {
    // Find the code block container
    const container = button.closest('.code-block-container')
    if (!container) {
      console.error('Could not find code block container')
      return
    }
    
    // Find the code element within the container
    const codeBlock = container.querySelector('code')
    if (!codeBlock) {
      console.error('Could not find code element')
      return
    }
    
    // Get the text content
    const text = codeBlock.textContent || codeBlock.innerText || ''
    
    // Copy to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showCopySuccess(button)
      }).catch(err => {
        console.error('Failed to copy with Clipboard API: ', err)
        fallbackCopy(text, button)
      })
    } else {
      fallbackCopy(text, button)
    }
  } catch (err) {
    console.error('Error in copyCodeBlock: ', err)
  }
}

// Show copy success feedback
const showCopySuccess = (button) => {
  const originalText = button.textContent
  button.textContent = 'Copied!'
  button.classList.add('bg-green-600', 'border-green-500')
  button.classList.remove('bg-gray-700', 'border-gray-600')
  
  setTimeout(() => {
    button.textContent = originalText
    button.classList.remove('bg-green-600', 'border-green-500')
    button.classList.add('bg-gray-700', 'border-gray-600')
  }, 2000)
}

// Fallback copy method for older browsers
const fallbackCopy = (text, button) => {
  try {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    
    const successful = document.execCommand('copy')
    document.body.removeChild(textArea)
    
    if (successful) {
      showCopySuccess(button)
    } else {
      console.error('Fallback copy failed')
    }
  } catch (err) {
    console.error('Fallback copy error: ', err)
  }
}

// Helper function to process message content (strings and structured objects)
const processMessageContent = (content) => {
  if (typeof content === 'string') {
    return content
  } else if (content && typeof content === 'object') {
    // Handle structured content objects that might contain markdown
    if (content.raw && typeof content.raw === 'string') {
      // If there's a raw property, use it (likely contains markdown)
      return content.raw
    } else if (content.text && typeof content.text === 'string') {
      // If there's a text property, use it
      return content.text
    } else {
      // Fallback to JSON for other objects
      try {
        return JSON.stringify(content, null, 2)
      } catch (e) {
        return String(content || '')
      }
    }
  } else {
    return String(content || '')
  }
}

// Helper function to filter out base64 data from tool arguments for display
const filterArgumentsForDisplay = (args) => {
  if (!args || typeof args !== 'object') return args
  
  const filteredArgs = { ...args }
  
  // Hide base64 data but show filename for context
  if (filteredArgs.file_data_base64) {
    const dataSize = filteredArgs.file_data_base64.length
    filteredArgs.file_data_base64 = `[File data: ${dataSize} characters - hidden for display]`
  }
  
  return filteredArgs
}

// Helper function to filter and enhance tool results for display
const processToolResult = (result) => {
  if (!result) return result
  
  if (typeof result === 'string') {
    try {
      // Try to parse as JSON to check for returned files
      const parsed = JSON.parse(result)
      return processToolResult(parsed)
    } catch (e) {
      // Not JSON, return as is
      return result
    }
  }
  
  if (typeof result === 'object') {
    const processed = { ...result }
    
    // Handle returned files
    if (processed.returned_file_base64 && processed.returned_file_name) {
      const dataSize = processed.returned_file_base64.length
      processed.returned_file_base64 = `[File data: ${dataSize} characters - hidden for display]`
      processed._file_download_available = true
    }
    
    // Hide any other base64 fields
    Object.keys(processed).forEach(key => {
      if (key.includes('base64') && key !== 'returned_file_base64') {
        if (typeof processed[key] === 'string' && processed[key].length > 100) {
          processed[key] = `[Base64 data: ${processed[key].length} characters - hidden for display]`
        }
      }
    })
    
    return processed
  }
  
  return result
}

// Helper function to download returned files
const downloadReturnedFile = (filename, base64Data) => {
  try {
    // Convert base64 to blob
    const byteCharacters = atob(base64Data)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    
    // Determine MIME type based on file extension
    const extension = filename.split('.').pop()?.toLowerCase()
    let mimeType = 'application/octet-stream'
    
    const mimeTypes = {
      'pdf': 'application/pdf',
      'txt': 'text/plain',
      'json': 'application/json',
      'csv': 'text/csv',
      'png': 'image/png',
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
      'gif': 'image/gif',
      'doc': 'application/msword',
      'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    
    if (extension && mimeTypes[extension]) {
      mimeType = mimeTypes[extension]
    }
    
    const blob = new Blob([byteArray], { type: mimeType })
    
    // Create download link and trigger download
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // Clean up
    setTimeout(() => URL.revokeObjectURL(url), 100)
    
  } catch (error) {
    console.error('Error downloading file:', error)
    alert('Failed to download file. Please try again.')
  }
}

const Message = ({ message }) => {
  const { appName } = useChat()
  
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  // Handle copy button clicks using event delegation
  useEffect(() => {
    const handleCopyClick = (event) => {
      if (event.target.matches('[data-action="copy-code"]')) {
        event.preventDefault()
        copyCodeBlock(event.target)
      }
    }

    document.addEventListener('click', handleCopyClick)
    return () => {
      document.removeEventListener('click', handleCopyClick)
    }
  }, [])
  
  const avatarBg = isUser ? 'bg-green-600' : isSystem ? 'bg-yellow-600' : 'bg-blue-600'
  const avatarText = isUser ? 'Y' : isSystem ? 'S' : 'A'
  const authorName = isUser ? 'You' : isSystem ? 'System' : appName
  
  const renderContent = () => {
    // Handle tool call messages specially
    if (message.type === 'tool_call') {
      return (
        <div className="text-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              message.status === 'calling' ? 'bg-blue-600' : 
              message.status === 'completed' ? 'bg-green-600' : 'bg-red-600'
            }`}>
              {message.status === 'calling' ? 'CALLING' : 
               message.status === 'completed' ? 'SUCCESS' : 'FAILED'}
            </span>
            <span className="font-medium">{message.tool_name}</span>
            <span className="text-gray-400 text-sm">({message.server_name})</span>
          </div>
          
          {/* Arguments Section */}
          {message.arguments && Object.keys(message.arguments).length > 0 && (
            <div className="mb-4">
              <div className="border-l-4 border-blue-500 pl-4">
                <h4 className="text-sm font-semibold text-blue-400 mb-2 flex items-center gap-2">
                  <span className="text-blue-400">▶</span> Input Arguments
                </h4>
                <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 max-h-64 overflow-y-auto">
                  <pre className="text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(filterArgumentsForDisplay(message.arguments), null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
          
          {/* Separator Line */}
          {message.arguments && Object.keys(message.arguments).length > 0 && message.result && (
            <div className="my-4">
              <hr className="border-gray-600" />
            </div>
          )}
          
          {/* Result Section */}
          {message.result && (
            <div className="mb-2">
              <div className="border-l-4 border-green-500 pl-4">
                <h4 className="text-sm font-semibold text-green-400 mb-2 flex items-center gap-2">
                  <span className="text-green-400">◀</span> Output Result
                </h4>
                
                {/* Check for returned file and show download button */}
                {(() => {
                  let parsedResult = message.result
                  if (typeof message.result === 'string') {
                    try {
                      parsedResult = JSON.parse(message.result)
                    } catch (e) {
                      parsedResult = message.result
                    }
                  }
                  
                  const hasReturnedFile = parsedResult && 
                    typeof parsedResult === 'object' && 
                    parsedResult.returned_file_name && 
                    parsedResult.returned_file_base64
                  
                  return hasReturnedFile ? (
                    <div className="mb-3">
                      <button
                        onClick={() => downloadReturnedFile(parsedResult.returned_file_name, parsedResult.returned_file_base64)}
                        className="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Download {parsedResult.returned_file_name}
                      </button>
                    </div>
                  ) : null
                })()}
                
                <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 max-h-64 overflow-y-auto">
                  <pre className="text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap">
                    {(() => {
                      const processedResult = processToolResult(message.result)
                      return typeof processedResult === 'string' ? processedResult : JSON.stringify(processedResult, null, 2)
                    })()}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )
    }
    
    if (isUser || isSystem) {
      return <div className="text-gray-200">{message.content}</div>
    }
    
    // Render markdown for assistant messages
    // Process content to handle both strings and structured objects
    const content = processMessageContent(message.content)
    
    try {
      const markdownHtml = marked.parse(content)
      const sanitizedHtml = DOMPurify.sanitize(markdownHtml)
      
      return (
        <div 
          className="text-gray-200 prose prose-invert max-w-none group"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
      )
    } catch (error) {
      console.error('Error parsing markdown content:', error)
      // Fallback to plain text if markdown parsing fails
      return (
        <div className="text-gray-200">
          <pre className="whitespace-pre-wrap">{content}</pre>
        </div>
      )
    }
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

export default memo(Message)