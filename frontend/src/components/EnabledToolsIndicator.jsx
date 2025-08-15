import { useChat } from '../contexts/ChatContext'

const EnabledToolsIndicator = () => {
  const { selectedTools, selectedPrompts } = useChat()

  const allToolNames = Array.from(selectedTools).map(key => {
    const parts = key.split('_')
    return parts.slice(1).join('_')
  })

  const allPromptNames = Array.from(selectedPrompts).map(key => {
    const parts = key.split('_')
    return parts.slice(1).join('_')
  })

  const total = allToolNames.length + allPromptNames.length
  if (total === 0) return null

  const items = [...allToolNames.map(n => ({ name: n, type: 'tool' })), ...allPromptNames.map(n => ({ name: n, type: 'prompt' }))]

  return (
    <div className="flex items-start gap-2 text-xs text-gray-400 mb-2">
      <span className="mt-1">Active:</span>
      <div className="flex-1 flex flex-wrap gap-1">
        {items.map((item, idx) => (
          <span
            key={idx}
            className={`px-2 py-1 rounded ${item.type === 'prompt' ? 'bg-purple-800 text-purple-200' : 'bg-gray-700 text-gray-300'}`}
          >
            {item.name}
          </span>
        ))}
      </div>
    </div>
  )
}

export default EnabledToolsIndicator