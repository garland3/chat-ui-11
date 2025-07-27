import { createContext, useContext, useState, useEffect } from 'react'
import { useChat } from './ChatContext'

const MarketplaceContext = createContext()

export const MarketplaceProvider = ({ children }) => {
  const { tools } = useChat()
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
      const allServers = tools.map(t => t.server)
      setSelectedServers(new Set(allServers))
      localStorage.setItem('mcp-selected-servers', JSON.stringify(allServers))
    }
  }, [tools])

  // Save to localStorage whenever selectedServers changes
  useEffect(() => {
    localStorage.setItem('mcp-selected-servers', JSON.stringify(Array.from(selectedServers)))
  }, [selectedServers])

  const toggleServer = (serverName) => {
    setSelectedServers(prev => {
      const newSet = new Set(prev)
      if (newSet.has(serverName)) {
        newSet.delete(serverName)
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
    const allServers = tools.map(t => t.server)
    setSelectedServers(new Set(allServers))
  }

  const deselectAllServers = () => {
    setSelectedServers(new Set())
  }

  const getFilteredTools = () => {
    return tools.filter(tool => selectedServers.has(tool.server))
  }

  const value = {
    selectedServers,
    toggleServer,
    isServerSelected,
    selectAllServers,
    deselectAllServers,
    getFilteredTools
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