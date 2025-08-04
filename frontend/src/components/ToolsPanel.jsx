import { X, Settings, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useChat } from '../contexts/ChatContext'
import { useMarketplace } from '../contexts/MarketplaceContext'
import ResizablePanel from './ResizablePanel'

const ToolsPanel = ({ isOpen, onClose }) => {
  const navigate = useNavigate()
  const { 
    selectedTools, 
    toggleTool, 
    selectedPrompts,
    togglePrompt,
    toolChoiceRequired, 
    setToolChoiceRequired,
    clearToolsAndPrompts
  } = useChat()
  const { getFilteredTools, getFilteredPrompts } = useMarketplace()
  
  // Use filtered tools and prompts instead of all tools
  const tools = getFilteredTools()
  const prompts = getFilteredPrompts()
  
  const navigateToMarketplace = () => {
    clearToolsAndPrompts()
    navigate('/marketplace')
  }

  // Combine tools and prompts into a unified server list
  const allServers = {}
  
  // Add tools to the unified list
  tools.forEach(toolServer => {
    if (!allServers[toolServer.server]) {
      allServers[toolServer.server] = {
        server: toolServer.server,
        description: toolServer.description,
        is_exclusive: toolServer.is_exclusive,
        tools: toolServer.tools || [],
        tool_count: toolServer.tool_count || 0,
        prompts: [],
        prompt_count: 0
      }
    }
  })
  
  // Add prompts to the unified list
  prompts.forEach(promptServer => {
    if (!allServers[promptServer.server]) {
      allServers[promptServer.server] = {
        server: promptServer.server,
        description: promptServer.description,
        is_exclusive: false,
        tools: [],
        tool_count: 0,
        prompts: promptServer.prompts || [],
        prompt_count: promptServer.prompt_count || 0
      }
    } else {
      allServers[promptServer.server].prompts = promptServer.prompts || []
      allServers[promptServer.server].prompt_count = promptServer.prompt_count || 0
    }
  })
  
  const serverList = Object.values(allServers)

  const toggleServerItems = (serverName) => {
    console.log('🔧 [TOOLS DEBUG] toggleServerItems called for server:', serverName)
    
    const server = serverList.find(s => s.server === serverName)
    if (!server) return

    // Get all tools and prompts for this server
    const serverToolKeys = server.tools.map(tool => `${serverName}_${tool}`)
    const serverPromptKeys = server.prompts.map(prompt => `${serverName}_${prompt.name}`)
    
    // Check if all items are selected
    const allToolsSelected = serverToolKeys.every(key => selectedTools.has(key))
    const allPromptsSelected = serverPromptKeys.every(key => selectedPrompts.has(key))
    const allSelected = allToolsSelected && allPromptsSelected
    
    console.log('🔧 [TOOLS DEBUG] Server tools:', serverToolKeys)
    console.log('🔧 [PROMPTS DEBUG] Server prompts:', serverPromptKeys)
    console.log('🔧 [DEBUG] All selected before toggle:', allSelected)

    if (allSelected) {
      // Deselect All: Remove all tools and prompts from this server
      console.log('🔧 [DEBUG] Deselecting all items from server:', serverName)
      serverToolKeys.forEach(key => {
        if (selectedTools.has(key)) {
          toggleTool(key)
        }
      })
      serverPromptKeys.forEach(key => {
        if (selectedPrompts.has(key)) {
          togglePrompt(key)
        }
      })
    } else {
      // Select All: Add all tools and prompts from this server
      console.log('🔧 [DEBUG] Selecting all items from server:', serverName)
      serverToolKeys.forEach(key => {
        if (!selectedTools.has(key)) {
          toggleTool(key)
        }
      })
      serverPromptKeys.forEach(key => {
        if (!selectedPrompts.has(key)) {
          togglePrompt(key)
        }
      })
    }
  }

  const getServerButtonText = (serverName) => {
    const server = serverList.find(s => s.server === serverName)
    if (!server) return 'Select All'

    const serverToolKeys = server.tools.map(tool => `${serverName}_${tool}`)
    const serverPromptKeys = server.prompts.map(prompt => `${serverName}_${prompt.name}`)
    const allKeys = [...serverToolKeys, ...serverPromptKeys]
    
    const selectedToolCount = serverToolKeys.filter(key => selectedTools.has(key)).length
    const selectedPromptCount = serverPromptKeys.filter(key => selectedPrompts.has(key)).length
    const selectedCount = selectedToolCount + selectedPromptCount

    if (selectedCount === 0) {
      return 'Select All'
    } else if (selectedCount === allKeys.length) {
      return 'Deselect All'
    } else {
      return `Select All (${selectedCount}/${allKeys.length})`
    }
  }

  const isServerSelected = (serverName) => {
    const server = serverList.find(s => s.server === serverName)
    if (!server) return false

    const serverToolKeys = server.tools.map(tool => `${serverName}_${tool}`)
    const serverPromptKeys = server.prompts.map(prompt => `${serverName}_${prompt.name}`)
    
    const allToolsSelected = serverToolKeys.every(key => selectedTools.has(key))
    const allPromptsSelected = serverPromptKeys.every(key => selectedPrompts.has(key))
    
    return allToolsSelected && allPromptsSelected && (serverToolKeys.length > 0 || serverPromptKeys.length > 0)
  }

  return (
    <ResizablePanel
      isOpen={isOpen}
      onClose={onClose}
      defaultWidth={448}
      minWidth={320}
      maxWidth={800}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
        <h2 className="text-lg font-semibold text-gray-100">Tools & Integrations</h2>
        <button
          onClick={onClose}
          className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

        {/* Tool Choice Controls */}
        <div className="p-4 border-b border-gray-700 flex-shrink-0">
          <div className="space-y-2">
            <button
              onClick={navigateToMarketplace}
              className="w-full px-4 py-2 rounded-lg border bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600 text-sm font-medium transition-colors"
            >
              Marketplace
            </button>
            <button
              onClick={() => setToolChoiceRequired(!toolChoiceRequired)}
              className={`w-full px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                toolChoiceRequired
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600'
              }`}
            >
              {toolChoiceRequired ? 'Required Tool Call (Active)' : 'Required Tool Call'}
            </button>
          </div>
        </div>

        {/* Tools & Prompts List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 min-h-0">
          {serverList.length === 0 ? (
            <div className="text-gray-400 text-center py-8">
              <div className="mb-4">No servers selected</div>
              <button
                onClick={navigateToMarketplace}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Go to Marketplace
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {serverList.map(server => (
                <div key={server.server} className="space-y-3">
                  {/* Server Header */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-white font-medium capitalize">
                        {server.server}
                      </h3>
                      <div className="flex items-center gap-2">
                        {server.tool_count > 0 && (
                          <span className="text-xs text-gray-400">
                            {server.tool_count} tools
                          </span>
                        )}
                        {server.prompt_count > 0 && (
                          <span className="text-xs text-purple-400">
                            {server.prompt_count} prompts
                          </span>
                        )}
                        {server.is_exclusive && (
                          <span className="px-2 py-1 bg-orange-600 text-xs rounded text-white">
                            Exclusive
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => toggleServerItems(server.server)}
                      className={`w-full px-3 py-2 rounded text-sm font-medium transition-colors ${
                        isServerSelected(server.server)
                          ? 'bg-blue-600 hover:bg-blue-700 text-white'
                          : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                      }`}
                    >
                      {getServerButtonText(server.server)}
                    </button>
                    
                    <p className="text-sm text-gray-400">{server.description}</p>
                  </div>

                  {/* Tools and Prompts */}
                  <div className="flex flex-wrap gap-2">
                    {/* Tools */}
                    {server.tools.map(tool => {
                      const toolKey = `${server.server}_${tool}`
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
                    
                    {/* Prompts */}
                    {server.prompts.map(prompt => {
                      const promptKey = `${server.server}_${prompt.name}`
                      const isSelected = selectedPrompts.has(promptKey)
                      
                      return (
                        <button
                          key={promptKey}
                          onClick={() => togglePrompt(promptKey)}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                            isSelected
                              ? 'bg-purple-600 text-white'
                              : 'bg-purple-700 hover:bg-purple-600 text-gray-300'
                          }`}
                          title={prompt.description}
                        >
                          {prompt.name}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
              
              {/* Clear Browser Memory Button */}
              <div className="mt-8 pt-4 border-t border-gray-700">
                <button
                  onClick={clearToolsAndPrompts}
                  className="w-full px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear Browser Memory
                </button>
                <p className="text-xs text-gray-400 mt-2 text-center">
                  Clears all saved tool and prompt selections
                </p>
              </div>
            </div>
          )}
        </div>
    </ResizablePanel>
  )
}

export default ToolsPanel