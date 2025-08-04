import { X } from 'lucide-react'
import { useChat } from '../contexts/ChatContext'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useState, useEffect } from 'react'

// Helper function to process canvas content (strings and structured objects)
const processCanvasContent = (content) => {
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


const MIN_WIDTH = 300;
const MAX_WIDTH = window.innerWidth * 0.9;

const CanvasPanel = ({ isOpen, onClose, onWidthChange }) => {
  const { canvasContent, customUIContent } = useChat();
  const [isMobile, setIsMobile] = useState(false);
  const [width, setWidth] = useState(() => {
    if (window.innerWidth < 768) return window.innerWidth;
    return Math.max(400, Math.min(window.innerWidth * 0.5, window.innerWidth * 0.9));
  });
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setWidth(window.innerWidth);
      } else {
        setWidth(Math.max(400, Math.min(window.innerWidth * 0.5, window.innerWidth * 0.9)));
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Notify parent component when width changes
  useEffect(() => {
    if (onWidthChange) {
      onWidthChange(isOpen ? width : 0);
    }
  }, [width, isOpen, onWidthChange]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      let newWidth = window.innerWidth - e.clientX;
      newWidth = Math.max(MIN_WIDTH, Math.min(newWidth, window.innerWidth * 0.9));
      setWidth(newWidth);
    };
    const handleMouseUp = () => setIsResizing(false);
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const renderContent = () => {
    // Priority: Custom UI content > Canvas content > Empty state
    if (customUIContent && customUIContent.type === 'html_injection') {
      return (
        <div className="p-4">
          <div className="mb-4 text-sm text-gray-400 border-b border-gray-700 pb-2">
            Custom UI from {customUIContent.serverName} - {customUIContent.toolName}
          </div>
          <div 
            className="prose prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(customUIContent.content) }}
          />
        </div>
      )
    }
    
    if (customUIContent && customUIContent.type === 'error') {
      return (
        <div className="p-4">
          <div className="text-red-400 text-center">
            {customUIContent.content}
          </div>
        </div>
      )
    }

    if (!canvasContent) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400">
          <p>Canvas content will appear here when the AI uses the canvas tool or when MCP servers provide custom UI content.</p>
        </div>
      )
    }

    // Process canvas content to handle both strings and structured objects
    const content = processCanvasContent(canvasContent)
    
    try {
      const markdownHtml = marked.parse(content)
      const sanitizedHtml = DOMPurify.sanitize(markdownHtml)

      return (
        <div 
          className="prose prose-invert max-w-none p-4"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
      )
    } catch (error) {
      console.error('Error parsing canvas markdown content:', error)
      // Fallback to plain text if markdown parsing fails
      return (
        <div className="p-4 text-gray-200">
          <pre className="whitespace-pre-wrap">{content}</pre>
        </div>
      )
    }
  }

  return (
    <aside
      className={`bg-gray-800 border-l border-gray-700 transform transition-all duration-300 ease-in-out ${isOpen ? 'flex flex-col' : 'hidden'}`}
      style={{
        width: isMobile ? '100vw' : `${width}px`,
        minWidth: isMobile ? '100vw' : `${MIN_WIDTH}px`,
        maxWidth: isMobile ? '100vw' : `${window.innerWidth * 0.9}px`,
        boxSizing: 'border-box',
      }}
    >
      {/* Draggable Divider */}
      {!isMobile && (
        <div
          style={{
            position: 'absolute',
            left: '-6px',
            top: 0,
            width: '12px',
            height: '100%',
            cursor: 'ew-resize',
            zIndex: 40,
          }}
          onMouseDown={() => setIsResizing(true)}
        >
          <div
            style={{
              width: '4px',
              height: '100%',
              margin: '0 auto',
              background: '#444',
              borderRadius: '2px',
              opacity: isResizing ? 0.8 : 0.5,
              transition: 'opacity 0.2s',
            }}
          />
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-900">
        <h2 className="text-lg font-semibold text-gray-100">Canvas</h2>
        <button
          onClick={onClose}
          className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {renderContent()}
      </div>
    </aside>
  );
};

export default CanvasPanel;