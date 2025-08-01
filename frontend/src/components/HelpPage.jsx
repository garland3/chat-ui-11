import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MessageSquare, Settings, Database, Store, Key, Zap, Code, FileText, AlertTriangle } from 'lucide-react'

const HelpPage = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
            title="Back to Chat"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-2xl font-bold">Help & Documentation</h1>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto p-6 space-y-8">
        
        {/* Quick Start */}
        <section className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <Zap className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-bold">Quick Start</h2>
          </div>
          <div className="space-y-4 text-gray-300">
            <p>Welcome to the Chat UI! This application provides an advanced chat interface with AI models, enhanced by powerful tools and data sources.</p>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-gray-700 p-4 rounded-lg">
                <h3 className="font-semibold text-white mb-2">🚀 Start a New Chat</h3>
                <p className="text-sm">Click "New Chat" button or press <kbd className="bg-gray-600 px-2 py-1 rounded text-xs">Ctrl+Alt+N</kbd></p>
              </div>
              <div className="bg-gray-700 p-4 rounded-lg">
                <h3 className="font-semibold text-white mb-2">🔧 Access Tools</h3>
                <p className="text-sm">Click the Settings icon <Settings className="w-4 h-4 inline" /> in the header to open the tools panel</p>
              </div>
            </div>
          </div>
        </section>

        {/* Core Features */}
        <section className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <MessageSquare className="w-6 h-6 text-green-400" />
            <h2 className="text-xl font-bold">Core Features</h2>
          </div>
          
          <div className="space-y-6">
            {/* RAG */}
            <div className="border-l-4 border-blue-400 pl-4">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-5 h-5 text-blue-400" />
                <h3 className="text-lg font-semibold">RAG (Retrieval-Augmented Generation)</h3>
              </div>
              <p className="text-gray-300 mb-2">Connect your chats to external data sources for enhanced, context-aware responses.</p>
              <ul className="text-sm text-gray-400 space-y-1 ml-4">
                <li>• Click the menu icon <Database className="w-4 h-4 inline" /> to open data sources panel</li>
                <li>• Select which documents/databases to include in your conversation</li>
                <li>• Toggle "RAG Only" mode to query only your documents without LLM processing</li>
                <li>• View source attribution to see which documents informed the response</li>
              </ul>
            </div>

            {/* Tools/MCP */}
            <div className="border-l-4 border-green-400 pl-4">
              <div className="flex items-center gap-2 mb-2">
                <Settings className="w-5 h-5 text-green-400" />
                <h3 className="text-lg font-semibold">Tools & MCP Servers</h3>
              </div>
              <p className="text-gray-300 mb-2">Extend AI capabilities with specialized tools through Model Context Protocol (MCP) servers.</p>
              <ul className="text-sm text-gray-400 space-y-1 ml-4">
                <li>• Click the Settings icon <Settings className="w-4 h-4 inline" /> to view available tools</li>
                <li>• Built-in tools include file operations, calculations, and UI demos</li>
                <li>• Tools can create interactive content in the Canvas panel</li>
                <li>• Select specific tools in the marketplace for personalized experience</li>
              </ul>
            </div>

            {/* MCP Store */}
            <div className="border-l-4 border-purple-400 pl-4">
              <div className="flex items-center gap-2 mb-2">
                <Store className="w-5 h-5 text-purple-400" />
                <h3 className="text-lg font-semibold">MCP Store/Marketplace</h3>
              </div>
              <p className="text-gray-300 mb-2">Browse and select MCP servers that provide different capabilities.</p>
              <ul className="text-sm text-gray-400 space-y-1 ml-4">
                <li>• Navigate to <code className="bg-gray-600 px-1 rounded">/marketplace</code> to browse available servers</li>
                <li>• Select which MCP servers you want to use in your chats</li>
                <li>• Each server provides specific tools and functionalities</li>
                <li>• Your selections are saved and persist across sessions</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Tips & Best Practices */}
        <section className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="w-6 h-6 text-yellow-400" />
            <h2 className="text-xl font-bold">Tips & Best Practices</h2>
          </div>
          
          <div className="space-y-4">
            <div className="bg-gray-700 p-4 rounded-lg">
              <h3 className="font-semibold text-white mb-2">💡 Starting Fresh Conversations</h3>
              <p className="text-gray-300 text-sm">For best results, start a new chat session when switching to a completely different topic. This prevents context confusion and ensures cleaner responses.</p>
            </div>
            
            <div className="bg-gray-700 p-4 rounded-lg">
              <h3 className="font-semibold text-white mb-2">⚠️ Handling Errors</h3>
              <p className="text-gray-300 text-sm">If you encounter errors or unexpected behavior, restart your chat session using the "New Chat" button. This clears the conversation history and resets the context.</p>
            </div>
            
            <div className="bg-gray-700 p-4 rounded-lg">
              <h3 className="font-semibold text-white mb-2">⌨️ Keyboard Shortcuts</h3>
              <div className="text-gray-300 text-sm space-y-1">
                <p><kbd className="bg-gray-600 px-2 py-1 rounded text-xs">Ctrl+Alt+N</kbd> - Start new chat</p>
                <p><kbd className="bg-gray-600 px-2 py-1 rounded text-xs">Enter</kbd> - Send message</p>
                <p><kbd className="bg-gray-600 px-2 py-1 rounded text-xs">Shift+Enter</kbd> - New line in message</p>
              </div>
            </div>
          </div>
        </section>

        {/* Technical Documentation */}
        <section className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <Code className="w-6 h-6 text-orange-400" />
            <h2 className="text-xl font-bold">Technical Documentation</h2>
          </div>
          
          <div className="space-y-6">
            {/* MCP Development */}
            <div className="border-l-4 border-orange-400 pl-4">
              <h3 className="text-lg font-semibold mb-2">Building Your Own MCP Server</h3>
              <p className="text-gray-300 mb-3">Create custom tools and functionality by developing your own MCP servers.</p>
              
              <div className="space-y-3">
                <div>
                  <h4 className="font-medium text-white">Special Return Types</h4>
                  <ul className="text-sm text-gray-400 space-y-1 ml-4">
                    <li>• <code className="bg-gray-600 px-1 rounded">custom_html</code> - Return custom HTML for Canvas rendering</li>
                    <li>• <code className="bg-gray-600 px-1 rounded">file_path</code> - Reference files for download/display</li>
                    <li>• <code className="bg-gray-600 px-1 rounded">content</code> - Standard text response</li>
                    <li>• <code className="bg-gray-600 px-1 rounded">success</code> - Boolean indicating operation success</li>
                  </ul>
                </div>
                
                <div>
                  <h4 className="font-medium text-white">Custom HTML Example</h4>
                  <pre className="bg-gray-900 p-3 rounded text-xs text-gray-300 overflow-x-auto">
{`return {
    "content": "Created interactive chart",
    "custom_html": "<div>Your HTML here</div>",
    "success": True
}`}
                  </pre>
                </div>
              </div>
            </div>

            {/* UI Modification */}
            <div className="border-l-4 border-cyan-400 pl-4">
              <h3 className="text-lg font-semibold mb-2">UI Modification & Custom Prompts</h3>
              <p className="text-gray-300 mb-3">Advanced customization options for developers.</p>
              
              <ul className="text-sm text-gray-400 space-y-1 ml-4">
                <li>• MCP servers can return custom HTML that renders in the Canvas panel</li>
                <li>• All HTML is sanitized for security using DOMPurify</li>
                <li>• JavaScript is supported for interactive elements</li>
                <li>• Use custom prompts to modify AI behavior</li>
                <li>• Create specialized tools for domain-specific tasks</li>
              </ul>
            </div>

            {/* Development Resources */}
            <div className="bg-gray-700 p-4 rounded-lg">
              <h3 className="font-semibold text-white mb-2">📚 Development Resources</h3>
              <div className="text-sm text-gray-300 space-y-1">
                <p>• <code className="bg-gray-600 px-1 rounded">docs/mcp-development.md</code> - Comprehensive MCP development guide</p>
                <p>• <code className="bg-gray-600 px-1 rounded">docs/advanced-features.md</code> - Advanced features and examples</p>
                <p>• <code className="bg-gray-600 px-1 rounded">docs/configuration.md</code> - Configuration options</p>
                <p>• <code className="bg-gray-600 px-1 rounded">backend/mcp/</code> - Example MCP server implementations</p>
              </div>
            </div>
          </div>
        </section>

        {/* Agent Mode */}
        <section className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-6 h-6 bg-gradient-to-br from-blue-400 to-purple-600 rounded-full flex items-center justify-center">
              <span className="text-xs font-bold">AI</span>
            </div>
            <h2 className="text-xl font-bold">Agent Mode</h2>
          </div>
          
          <div className="text-gray-300 space-y-3">
            <p>Agent mode enables multi-step reasoning where the AI breaks down complex tasks into manageable steps.</p>
            
            <div className="bg-gray-700 p-4 rounded-lg">
              <h3 className="font-semibold text-white mb-2">Features</h3>
              <ul className="text-sm space-y-1">
                <li>• Step-by-step task breakdown and execution</li>
                <li>• Visual progress tracking</li>
                <li>• Integration with MCP tools during reasoning</li>
                <li>• Ability to interrupt the reasoning process</li>
              </ul>
            </div>
            
            <p className="text-sm text-gray-400">
              <strong>Note:</strong> Agent mode availability depends on your configuration. 
              Check with your administrator if this feature is not visible.
            </p>
          </div>
        </section>

        {/* Support */}
        <section className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-6 h-6 text-gray-400" />
            <h2 className="text-xl font-bold">Need More Help?</h2>
          </div>
          
          <div className="text-gray-300 space-y-3">
            <p>For additional information and detailed guides:</p>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-gray-700 p-4 rounded-lg">
                <h3 className="font-semibold text-white mb-2">📖 Documentation</h3>
                <p className="text-sm">Check the <code className="bg-gray-600 px-1 rounded">docs/</code> folder for comprehensive guides on setup, configuration, and development.</p>
              </div>
              <div className="bg-gray-700 p-4 rounded-lg">
                <h3 className="font-semibold text-white mb-2">🔧 Configuration</h3>
                <p className="text-sm">Refer to <code className="bg-gray-600 px-1 rounded">.env.example</code> and configuration documentation for customization options.</p>
              </div>
            </div>
          </div>
        </section>
        
      </div>
    </div>
  )
}

export default HelpPage