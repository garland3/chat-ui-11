import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, X } from 'lucide-react'
import { useChat } from '../contexts/ChatContext'
import { useMarketplace } from '../contexts/MarketplaceContext'

const MarketplacePanel = () => {
  const navigate = useNavigate()
  const { tools, prompts } = useChat()
  const {
    selectedServers,
    toggleServer,
    isServerSelected,
    selectAllServers,
    deselectAllServers
  } = useMarketplace()

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
  const selectedCount = selectedServers.size
  const totalCount = serverList.length

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
              title="Back to Chat"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">MCP Marketplace</h1>
              <p className="text-sm text-gray-400">
                Select which MCP servers to use in your chat interface
              </p>
            </div>
          </div>
          <div className="text-sm text-gray-400">
            {selectedCount} of {totalCount} servers selected
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto p-6">
        {/* Controls */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={selectAllServers}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Select All
          </button>
          <button
            onClick={deselectAllServers}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors"
          >
            Deselect All
          </button>
        </div>

        {/* Server Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {serverList.map((server) => {
            const isSelected = isServerSelected(server.server)
            
            return (
              <div
                key={server.server}
                className={`
                  relative p-6 rounded-lg border-2 transition-all cursor-pointer
                  ${isSelected 
                    ? 'border-blue-500 bg-blue-500/10' 
                    : 'border-gray-600 bg-gray-800 hover:border-gray-500'
                  }
                `}
                onClick={() => toggleServer(server.server)}
              >
                {/* Selection Indicator */}
                <div className={`
                  absolute top-4 right-4 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors
                  ${isSelected 
                    ? 'border-blue-500 bg-blue-500' 
                    : 'border-gray-500'
                  }
                `}>
                  {isSelected && <Check className="w-4 h-4 text-white" />}
                </div>

                {/* Server Info */}
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-white capitalize mb-2">
                    {server.server}
                  </h3>
                  <p className="text-sm text-gray-400 mb-3">
                    {server.description}
                  </p>
                  
                  {/* Server Stats */}
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    {server.tool_count > 0 && <span>{server.tool_count} tools</span>}
                    {server.prompt_count > 0 && <span>{server.prompt_count} prompts</span>}
                    {server.is_exclusive && (
                      <span className="px-2 py-1 bg-orange-600 text-white rounded">
                        Exclusive
                      </span>
                    )}
                  </div>
                </div>

                {/* Tools and Prompts Preview */}
                <div className="flex flex-wrap gap-1">
                  {/* Tools */}
                  {server.tools.slice(0, 4).map((tool) => (
                    <span
                      key={tool}
                      className="px-2 py-1 bg-gray-700 text-xs rounded text-gray-300"
                    >
                      {tool}
                    </span>
                  ))}
                  
                  {/* Prompts */}
                  {server.prompts.slice(0, 4).map((prompt) => (
                    <span
                      key={prompt.name}
                      className="px-2 py-1 bg-purple-700 text-xs rounded text-gray-300"
                      title={prompt.description}
                    >
                      {prompt.name}
                    </span>
                  ))}
                  
                  {/* Show "more" indicator */}
                  {(server.tools.length + server.prompts.length) > 4 && (
                    <span className="px-2 py-1 bg-gray-700 text-xs rounded text-gray-300">
                      +{(server.tools.length + server.prompts.length) - 4} more
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {serverList.length === 0 && (
          <div className="text-center py-12">
            <X className="w-16 h-16 text-gray-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">
              No MCP Servers Available
            </h3>
            <p className="text-gray-500">
              No MCP servers are currently authorized for your account.
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="mt-8 p-4 bg-gray-800 rounded-lg">
          <h4 className="font-medium text-gray-200 mb-2">How it works:</h4>
          <ul className="text-sm text-gray-400 space-y-1">
            <li>• Select the MCP servers you want to use in your chat interface</li>
            <li>• Only selected servers will appear in the Tools & Integrations panel</li>
            <li>• <span className="text-purple-400">Purple tags</span> indicate custom prompts, <span className="text-gray-300">gray tags</span> indicate tools</li>
            <li>• Your selections are saved in your browser</li>
            <li>• You can change your selection anytime by returning to this marketplace</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default MarketplacePanel