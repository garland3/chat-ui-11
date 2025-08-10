import { createContext, useContext, useState, useEffect } from 'react'
import { useChat } from './ChatContext'

const MarketplaceContext = createContext()

export const MarketplaceProvider = ({ children }) => {
  const { tools, prompts } = useChat()
  const [selectedServers, setSelectedServers] = useState(new Set())

  // Load selected servers from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('mcp-selected-servers')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        setSelectedServers(new Set(parsed))
      } catch (error) {
        console.error('Failed to parse stored selected servers:', error)
      }
    } else {
      // Initialize with all available servers by default
      const toolServers = tools.map(t => t.server)
      const promptServers = prompts.map(p => p.server)
      const allServers = [...new Set([...toolServers, ...promptServers])]
      setSelectedServers(new Set(allServers))
      localStorage.setItem('mcp-selected-servers', JSON.stringify(allServers))
    }
  }, [tools, prompts])

  // Save to localStorage whenever selectedServers changes
  useEffect(() => {
    localStorage.setItem('mcp-selected-servers', JSON.stringify(Array.from(selectedServers)))
  }, [selectedServers])

  const toggleServer = (serverName) => {
    setSelectedServers(prev => {
      const newSet = new Set(prev)
      if (newSet.has(serverName)) {
        newSet.delete(serverName)
        // Clear tool and prompt selections for deselected server
        clearServerMemory(serverName)
      } else {
        newSet.add(serverName)
      }
      return newSet
    })
  }

  const isServerSelected = (serverName) => {
    return selectedServers.has(serverName)
  }

  const selectAllServers = () => {
    const toolServers = tools.map(t => t.server)
    const promptServers = prompts.map(p => p.server)
    const allServers = [...new Set([...toolServers, ...promptServers])]
    setSelectedServers(new Set(allServers))
  }

  const deselectAllServers = () => {
    // Clear memory for all servers before deselecting
    selectedServers.forEach(serverName => clearServerMemory(serverName))
    setSelectedServers(new Set())
  }

  const clearServerMemory = (serverName) => {
    // Clear tool selections for this server from localStorage
    try {
      const savedTools = localStorage.getItem('chatui-selected-tools')
      if (savedTools) {
        const toolSelections = JSON.parse(savedTools)
        const filteredTools = toolSelections.filter(toolKey => !toolKey.startsWith(`${serverName}_`))
        localStorage.setItem('chatui-selected-tools', JSON.stringify(filteredTools))
      }
    } catch (error) {
      console.warn('Failed to clear tool selections for server:', serverName, error)
    }

    // Clear prompt selections for this server from localStorage
    try {
      const savedPrompts = localStorage.getItem('chatui-selected-prompts')
      if (savedPrompts) {
        const promptSelections = JSON.parse(savedPrompts)
        const filteredPrompts = promptSelections.filter(promptKey => !promptKey.startsWith(`${serverName}_`))
        localStorage.setItem('chatui-selected-prompts', JSON.stringify(filteredPrompts))
      }
    } catch (error) {
      console.warn('Failed to clear prompt selections for server:', serverName, error)
    }
  }

  const getFilteredTools = () => {
    return tools.filter(tool => selectedServers.has(tool.server))
  }

  const getFilteredPrompts = () => {
    return prompts.filter(prompt => selectedServers.has(prompt.server))
  }

  const value = {
    selectedServers,
    toggleServer,
    isServerSelected,
    selectAllServers,
    deselectAllServers,
    getFilteredTools,
    getFilteredPrompts
  }

  return (
    <MarketplaceContext.Provider value={value}>
      {children}
    </MarketplaceContext.Provider>
  )
}

export const useMarketplace = () => {
  const context = useContext(MarketplaceContext)
  if (!context) {
    throw new Error('useMarketplace must be used within MarketplaceProvider')
  }
  return context
}