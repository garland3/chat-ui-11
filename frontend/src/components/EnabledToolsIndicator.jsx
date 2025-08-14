import { useChat } from '../contexts/ChatContext'
import { useMarketplace } from '../contexts/MarketplaceContext'

const EnabledToolsIndicator = () => {
  const { selectedTools, selectedPrompts } = useChat()
  const { getFilteredTools, getFilteredPrompts } = useMarketplace()
  
  const enabledToolsCount = selectedTools.size
  const enabledPromptsCount = selectedPrompts.size
  const totalEnabled = enabledToolsCount + enabledPromptsCount
  
  if (totalEnabled === 0) return null
  
  // Get first few enabled tools/prompts for display
  const toolNames = Array.from(selectedTools).slice(0, 2).map(key => {
    const [server, tool] = key.split('_')
    return tool
  })
  
  const promptNames = Array.from(selectedPrompts).slice(0, 2).map(key => {
    const [server, prompt] = key.split('_')
    return prompt
  })
  
  const displayItems = [...toolNames, ...promptNames]
  const remaining = totalEnabled - displayItems.length
  
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
      <span>Active:</span>
      <div className="flex items-center gap-1 flex-wrap">
        {displayItems.map((item, index) => (
          <span 
            key={index}
            className="px-2 py-1 bg-gray-700 rounded text-gray-300"
          >
            {item}
          </span>
        ))}
        {remaining > 0 && (
          <span className="text-gray-500">
            +{remaining} more
          </span>
        )}
      </div>
    </div>
  )
}

export default EnabledToolsIndicator