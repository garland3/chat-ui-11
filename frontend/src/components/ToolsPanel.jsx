import { X, Trash2, Search, Plus, Wrench, ChevronDown, ChevronUp } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useChat } from '../contexts/ChatContext'
import { useMarketplace } from '../contexts/MarketplaceContext'

const ToolsPanel = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedServers, setExpandedServers] = useState(new Set())
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


  const toggleServerExpansion = (serverName) => {
    const newExpanded = new Set(expandedServers)
    if (newExpanded.has(serverName)) {
      newExpanded.delete(serverName)
    } else {
      newExpanded.add(serverName)
    }
    setExpandedServers(newExpanded)
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

        {/* Controls Section */}
        <div className="p-6 border-b border-gray-700 flex-shrink-0 space-y-6">
          {/* Add from Marketplace Button */}
          <button
            onClick={navigateToMarketplace}
            className="w-full px-6 py-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors flex items-center justify-center gap-3"
          >
            <Plus className="w-5 h-5" />
            Add from Marketplace
          </button>
          
          {/* Required Tool Usage Toggle */}
          <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
            <div>
              <h3 className="text-white font-medium">Required Tool Usage</h3>
              <p className="text-sm text-gray-400 mt-1">
                When enabled, the model must use one of your selected tools to respond.
              </p>
            </div>
            <button
              onClick={() => setToolChoiceRequired(!toolChoiceRequired)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 ${
                toolChoiceRequired ? 'bg-blue-600' : 'bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  toolChoiceRequired ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Tools List */}
        <div className="flex-1 overflow-y-auto custom-scrollbar min-h-0">
          {serverList.length === 0 ? (
            <div className="text-gray-400 text-center py-12 px-6">
              <div className="text-lg mb-4">No servers selected</div>
              <p className="mb-6 text-gray-500">Add MCP servers from the marketplace to enable tools and integrations</p>
              <button
                onClick={navigateToMarketplace}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
              >
                Browse Marketplace
              </button>
            </div>
          ) : (
            <>
              {/* Section Header */}
              <div className="px-6 py-4 border-b border-gray-700">
                <h3 className="text-lg font-semibold text-white">
                  Your Installed Tools ({serverList.reduce((total, server) => total + server.tool_count + server.prompt_count, 0)})
                </h3>
              </div>
              
              {/* Search Bar */}
              <div className="px-6 py-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="Search installed tools..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
              
              {filteredServers.length === 0 ? (
                <div className="text-gray-400 text-center py-12 px-6">
                  <div className="text-lg mb-4">No results found</div>
                  <p className="text-gray-500">Try adjusting your search terms</p>
                </div>
              ) : (
                <div className="px-6 pb-6 space-y-4">
                  {filteredServers.map(server => {
                    const isExpanded = expandedServers.has(server.server)
                    const hasIndividualItems = server.tools.length > 0 || server.prompts.length > 0
                    
                    return (
                      <div key={server.server} className="bg-gray-700 rounded-lg overflow-hidden">
                        {/* Main Server Row */}
                        <div className="p-4 flex items-center gap-4">
                          {/* Server Icon */}
                          <div className="bg-gray-600 rounded-lg p-3 flex-shrink-0">
                            <Wrench className="w-6 h-6 text-gray-300" />
                          </div>
                          
                          {/* Server Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <h3 className="text-white font-semibold text-lg capitalize truncate">
                                {server.server}
                              </h3>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                {server.is_exclusive && (
                                  <span className="px-2 py-1 bg-orange-600 text-xs rounded text-white">
                                    Exclusive
                                  </span>
                                )}
                              </div>
                            </div>
                            <p className="text-sm text-gray-400 truncate">{server.description}</p>
                            
                            {/* Tools and Prompts Count */}
                            <div className="flex items-center gap-4 mt-2">
                              {server.tool_count > 0 && (
                                <span className="text-xs text-gray-300">
                                  {server.tool_count} tool{server.tool_count !== 1 ? 's' : ''}
                                </span>
                              )}
                              {server.prompt_count > 0 && (
                                <span className="text-xs text-purple-300">
                                  {server.prompt_count} prompt{server.prompt_count !== 1 ? 's' : ''}
                                </span>
                              )}
                            </div>
                          </div>
                          
                          {/* Action Buttons */}
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {/* Expand Button */}
                            {hasIndividualItems && (
                              <button
                                onClick={() => toggleServerExpansion(server.server)}
                                className="p-2 rounded-lg bg-gray-600 hover:bg-gray-500 text-gray-300 transition-colors"
                                title="Show individual tools"
                              >
                                {isExpanded ? (
                                  <ChevronUp className="w-4 h-4" />
                                ) : (
                                  <ChevronDown className="w-4 h-4" />
                                )}
                              </button>
                            )}
                            
                            {/* Toggle All Button */}
                            <button
                              onClick={() => toggleServerItems(server.server)}
                              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                                isServerSelected(server.server)
                                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                  : 'bg-gray-600 hover:bg-gray-500 text-gray-200'
                              }`}
                            >
                              {isServerSelected(server.server) ? 'Enabled' : 'Enable'}
                            </button>
                          </div>
                        </div>
                        
                        {/* Expanded Individual Tools Section */}
                        {isExpanded && hasIndividualItems && (
                          <div className="px-4 pb-4 border-t border-gray-600 bg-gray-800">
                            <div className="pt-4 space-y-3">
                              <p className="text-sm text-gray-400 mb-3">
                                Select individual tools and prompts:
                              </p>
                              
                              {/* Tools */}
                              {server.tools.length > 0 && (
                                <div>
                                  <h4 className="text-sm font-medium text-gray-300 mb-2">Tools</h4>
                                  <div className="space-y-2">
                                    {server.tools.map(tool => {
                                      const toolKey = `${server.server}_${tool}`
                                      const isSelected = selectedTools.has(toolKey)
                                      
                                      return (
                                        <label
                                          key={toolKey}
                                          className="flex items-center gap-3 p-2 rounded bg-gray-600 hover:bg-gray-500 cursor-pointer transition-colors"
                                        >
                                          <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => toggleTool(toolKey)}
                                            className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                                          />
                                          <span className="text-sm text-gray-200">{tool}</span>
                                        </label>
                                      )
                                    })}
                                  </div>
                                </div>
                              )}
                              
                              {/* Prompts */}
                              {server.prompts.length > 0 && (
                                <div>
                                  <h4 className="text-sm font-medium text-purple-300 mb-2">Prompts</h4>
                                  <div className="space-y-2">
                                    {server.prompts.map(prompt => {
                                      const promptKey = `${server.server}_${prompt.name}`
                                      const isSelected = selectedPrompts.has(promptKey)
                                      
                                      return (
                                        <label
                                          key={promptKey}
                                          className="flex items-center gap-3 p-2 rounded bg-purple-900 hover:bg-purple-800 cursor-pointer transition-colors"
                                          title={prompt.description}
                                        >
                                          <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => togglePrompt(promptKey)}
                                            className="w-4 h-4 text-purple-600 bg-gray-700 border-gray-600 rounded focus:ring-purple-500 focus:ring-2"
                                          />
                                          <div className="flex-1 min-w-0">
                                            <span className="text-sm text-gray-200 block truncate">{prompt.name}</span>
                                            {prompt.description && (
                                              <span className="text-xs text-gray-400 block truncate mt-1">
                                                {prompt.description}
                                              </span>
                                            )}
                                          </div>
                                        </label>
                                      )
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
              
              {/* Clear All Button - Made smaller and less prominent */}
              <div className="px-6 pb-6">
                <div className="pt-4 border-t border-gray-600 flex justify-center">
                  <button
                    onClick={clearToolsAndPrompts}
                    className="px-3 py-1.5 text-xs rounded bg-gray-600 hover:bg-red-600 text-gray-300 hover:text-white transition-colors flex items-center gap-1.5"
                    title="Clear all tool and prompt selections"
                  >
                    <Trash2 className="w-3 h-3" />
                    Clear All
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default ToolsPanel