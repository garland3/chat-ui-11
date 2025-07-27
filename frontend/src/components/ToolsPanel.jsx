import { X, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useChat } from '../contexts/ChatContext'
import { useMarketplace } from '../contexts/MarketplaceContext'

const ToolsPanel = ({ isOpen, onClose }) => {
  const navigate = useNavigate()
  const { 
    selectedTools, 
    toggleTool, 
    toolChoiceRequired, 
    setToolChoiceRequired 
  } = useChat()
  const { getFilteredTools } = useMarketplace()
  
  // Use filtered tools instead of all tools
  const tools = getFilteredTools()

  const toggleServerTools = (serverName) => {
    console.log('🔧 [TOOLS DEBUG] toggleServerTools called for server:', serverName)
    
    const serverTools = tools.find(t => t.server === serverName)
    if (!serverTools) return

    const serverToolKeys = serverTools.tools.map(tool => `${serverName}_${tool}`)
    const allSelected = serverToolKeys.every(key => selectedTools.has(key))
    
    console.log('🔧 [TOOLS DEBUG] Server tools:', serverToolKeys)
    console.log('🔧 [TOOLS DEBUG] All selected before toggle:', allSelected)
    console.log('🔧 [TOOLS DEBUG] Currently selected tools:', Array.from(selectedTools))

    if (allSelected) {
      // Deselect All: Remove all tools from this server
      console.log('🔧 [TOOLS DEBUG] Deselecting all tools from server:', serverName)
      serverToolKeys.forEach(key => {
        console.log('🔧 [TOOLS DEBUG] Deselecting tool:', key)
        toggleTool(key) // This will remove if selected
      })
    } else {
      // Select All: Add all tools from this server
      console.log('🔧 [TOOLS DEBUG] Selecting all tools from server:', serverName)
      serverToolKeys.forEach(key => {
        console.log('🔧 [TOOLS DEBUG] Selecting tool:', key)
        if (!selectedTools.has(key)) {
          toggleTool(key) // Only toggle if not already selected
        }
      })
    }
  }

  const getServerButtonText = (serverName) => {
    const serverTools = tools.find(t => t.server === serverName)
    if (!serverTools) return 'Select All'

    const serverToolKeys = serverTools.tools.map(tool => `${serverName}_${tool}`)
    const selectedCount = serverToolKeys.filter(key => selectedTools.has(key)).length

    if (selectedCount === 0) {
      return 'Select All'
    } else if (selectedCount === serverToolKeys.length) {
      return 'Deselect All'
    } else {
      return `Select All (${selectedCount}/${serverToolKeys.length})`
    }
  }

  const isServerSelected = (serverName) => {
    const serverTools = tools.find(t => t.server === serverName)
    if (!serverTools) return false

    const serverToolKeys = serverTools.tools.map(tool => `${serverName}_${tool}`)
    return serverToolKeys.every(key => selectedTools.has(key))
  }

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Panel */}
      <aside className={`
        fixed right-0 top-0 h-full w-80 bg-gray-800 border-l border-gray-700 z-50 transform transition-transform duration-300 ease-in-out flex flex-col
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        lg:relative lg:translate-x-0 lg:w-96
        ${!isOpen ? 'lg:hidden' : ''}
      `}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-100">Tools & Integrations</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/marketplace')}
              className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
              title="MCP Marketplace"
            >
              <Settings className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tool Choice Controls */}
        <div className="p-4 border-b border-gray-700 flex-shrink-0">
          <button
            onClick={() => setToolChoiceRequired(!toolChoiceRequired)}
            className={`w-full px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
              toolChoiceRequired
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600'
            }`}
          >
            {toolChoiceRequired ? 'Required (Active)' : 'Required'}
          </button>
        </div>

        {/* Tools List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 min-h-0">
          {tools.length === 0 ? (
            <div className="text-gray-400 text-center py-8">
              <div className="mb-4">No servers selected</div>
              <button
                onClick={() => navigate('/marketplace')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Go to Marketplace
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {tools.map(toolServer => (
                <div key={toolServer.server} className="space-y-3">
                  {/* Server Header */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-white font-medium capitalize">
                        {toolServer.server}
                      </h3>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">
                          {toolServer.tool_count} tools
                        </span>
                        {toolServer.is_exclusive && (
                          <span className="px-2 py-1 bg-orange-600 text-xs rounded text-white">
                            Exclusive
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => toggleServerTools(toolServer.server)}
                      className={`w-full px-3 py-2 rounded text-sm font-medium transition-colors ${
                        isServerSelected(toolServer.server)
                          ? 'bg-blue-600 hover:bg-blue-700 text-white'
                          : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                      }`}
                    >
                      {getServerButtonText(toolServer.server)}
                    </button>
                    
                    <p className="text-sm text-gray-400">{toolServer.description}</p>
                  </div>

                  {/* Tools */}
                  <div className="flex flex-wrap gap-2">
                    {toolServer.tools.map(tool => {
                      const toolKey = `${toolServer.server}_${tool}`
                      const isSelected = selectedTools.has(toolKey)
                      
                      return (
                        <button
                          key={toolKey}
                          onClick={() => toggleTool(toolKey)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                            isSelected
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                          }`}
                        >
                          {tool}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

export default ToolsPanel