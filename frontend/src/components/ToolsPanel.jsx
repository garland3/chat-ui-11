import { X, Trash2, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useChat } from '../contexts/ChatContext'
import { useMarketplace } from '../contexts/MarketplaceContext'

const ToolsPanel = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('')
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

  // Filter servers based on search term
  const filteredServers = serverList.filter(server => {
    if (!searchTerm) return true
    
    const searchLower = searchTerm.toLowerCase()
    
    // Search in server name and description
    if (server.server.toLowerCase().includes(searchLower) || 
        server.description.toLowerCase().includes(searchLower)) {
      return true
    }
    
    // Search in tool names
    if (server.tools.some(tool => tool.toLowerCase().includes(searchLower))) {
      return true
    }
    
    // Search in prompt names and descriptions
    if (server.prompts.some(prompt => 
      prompt.name.toLowerCase().includes(searchLower) || 
      prompt.description.toLowerCase().includes(searchLower)
    )) {
      return true
    }
    
    return false
  })

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

  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div 
        className="bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] mx-4 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700 flex-shrink-0">
          <h2 className="text-xl font-semibold text-gray-100">Tools & Integrations</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tool Choice Controls */}
        <div className="p-6 border-b border-gray-700 flex-shrink-0">
          <div className="flex gap-4 mb-4">
            <button
              onClick={navigateToMarketplace}
              className="px-6 py-3 rounded-lg border bg-blue-600 border-blue-500 text-white hover:bg-blue-700 font-medium transition-colors"
            >
              Add from Marketplace
            </button>
          </div>
          
          {/* Required Tool Call Section */}
          <div className="space-y-2">
            <button
              onClick={() => setToolChoiceRequired(!toolChoiceRequired)}
              className={`w-full px-6 py-3 rounded-lg border font-medium transition-colors ${
                toolChoiceRequired
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600'
              }`}
            >
              {toolChoiceRequired ? 'Required Tool Call (Active)' : 'Required Tool Call'}
            </button>
            <p className="text-sm text-gray-400">
              When enabled, Claude must use one of your selected tools to respond. Useful for ensuring tool usage in workflows.
            </p>
          </div>

          {/* Search Bar */}
          <div className="mt-4 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search tools and integrations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Tools & Prompts List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 min-h-0">
          {serverList.length === 0 ? (
            <div className="text-gray-400 text-center py-12">
              <div className="text-lg mb-4">No servers selected</div>
              <p className="mb-6 text-gray-500">Add MCP servers from the marketplace to enable tools and integrations</p>
              <button
                onClick={navigateToMarketplace}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
              >
                Browse Marketplace
              </button>
            </div>
          ) : filteredServers.length === 0 ? (
            <div className="text-gray-400 text-center py-12">
              <div className="text-lg mb-4">No results found</div>
              <p className="text-gray-500">Try adjusting your search terms</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredServers.map(server => (
                  <div key={server.server} className="bg-gray-700 rounded-lg p-4 space-y-3">
                    {/* Server Header */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-white font-semibold text-lg capitalize">
                          {server.server}
                        </h3>
                        <div className="flex items-center gap-2">
                          {server.tool_count > 0 && (
                            <span className="text-xs text-gray-300 bg-gray-600 px-2 py-1 rounded">
                              {server.tool_count} tools
                            </span>
                          )}
                          {server.prompt_count > 0 && (
                            <span className="text-xs text-purple-300 bg-purple-600 px-2 py-1 rounded">
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
                            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                              isSelected
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'bg-gray-600 hover:bg-gray-500 text-gray-200'
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
                            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                              isSelected
                                ? 'bg-purple-600 text-white shadow-md'
                                : 'bg-purple-700 hover:bg-purple-600 text-gray-200'
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
              </div>
              
              {/* Clear Browser Memory Button */}
              <div className="mt-8 pt-6 border-t border-gray-600 text-center">
                <button
                  onClick={clearToolsAndPrompts}
                  className="px-6 py-3 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors flex items-center justify-center gap-2 mx-auto"
                >
                  <Trash2 className="w-4 h-4" />
                  Clear All Selections
                </button>
                <p className="text-sm text-gray-400 mt-2">
                  Clears all saved tool and prompt selections
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default ToolsPanel