import { X } from 'lucide-react'
import { useChat } from '../contexts/ChatContext'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const CanvasPanel = ({ isOpen, onClose }) => {
  const { canvasContent } = useChat()

  const renderContent = () => {
    if (!canvasContent) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400">
          <p>Canvas content will appear here when the AI uses the canvas tool.</p>
        </div>
      )
    }

    // Ensure content is a string before parsing
    const content = typeof canvasContent === 'string' ? canvasContent : String(canvasContent || '')
    const markdownHtml = marked.parse(content)
    const sanitizedHtml = DOMPurify.sanitize(markdownHtml)

    return (
      <div 
        className="prose prose-invert max-w-none p-4"
        dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
      />
    )
  }

  return (
    <aside className={`
      absolute right-0 top-0 h-full w-1/2 bg-gray-800 border-l border-gray-700 z-30 transform transition-transform duration-300 ease-in-out
      ${isOpen ? 'translate-x-0' : 'translate-x-full'}
    `}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-gray-100">Canvas</h2>
        <button
          onClick={onClose}
          className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar h-full pb-16">
        {renderContent()}
      </div>
    </aside>
  )
}

export default CanvasPanel