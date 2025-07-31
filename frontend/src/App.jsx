import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ChatProvider, useChat } from './contexts/ChatContext'
import { WSProvider } from './contexts/WSContext'
import { MarketplaceProvider } from './contexts/MarketplaceContext'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import ToolsPanel from './components/ToolsPanel'
import RagPanel from './components/RagPanel'
import CanvasPanel from './components/CanvasPanel'
import AgentModal from './components/AgentModal'
import MarketplacePanel from './components/MarketplacePanel'
import BannerPanel from './components/BannerPanel'

function ChatInterface() {
  const [toolsPanelOpen, setToolsPanelOpen] = useState(false)
  const [ragPanelOpen, setRagPanelOpen] = useState(false)
  const [canvasPanelOpen, setCanvasPanelOpen] = useState(false)
  const [agentModalOpen, setAgentModalOpen] = useState(false)
  const [canvasPanelWidth, setCanvasPanelWidth] = useState(0)
  const { canvasContent, customUIContent } = useChat()

  // Auto-open tools panel when returning from marketplace
  useEffect(() => {
    const shouldOpenToolsPanel = sessionStorage.getItem('openToolsPanel')
    if (shouldOpenToolsPanel === 'true') {
      setToolsPanelOpen(true)
      sessionStorage.removeItem('openToolsPanel') // Clear the flag
    }
  }, [])

  // Auto-open canvas panel when content is received
  useEffect(() => {
    if (canvasContent && canvasContent.trim()) {
      setCanvasPanelOpen(true)
    }
  }, [canvasContent])

  // Auto-open canvas panel when custom UI content is received
  useEffect(() => {
    if (customUIContent) {
      setCanvasPanelOpen(true)
    }
  }, [customUIContent])

  return (
    <div className="flex h-screen w-full bg-gray-900 text-gray-200">
      {/* RAG Data Sources Panel */}
      <RagPanel 
        isOpen={ragPanelOpen} 
        onClose={() => setRagPanelOpen(false)} 
      />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 relative">
        {/* Banner Panel - positioned at the very top */}
        <BannerPanel />
        
        {/* Canvas Panel */}
        <CanvasPanel 
          isOpen={canvasPanelOpen}
          onClose={() => setCanvasPanelOpen(false)}
          onWidthChange={setCanvasPanelWidth}
        />

        {/* Header */}
        <Header 
          onToggleRag={() => setRagPanelOpen(!ragPanelOpen)}
          onToggleTools={() => setToolsPanelOpen(!toolsPanelOpen)}
          onToggleAgent={() => setAgentModalOpen(!agentModalOpen)}
        />

        {/* Chat Area */}
        <ChatArea 
          canvasPanelOpen={canvasPanelOpen} 
          canvasPanelWidth={canvasPanelWidth}
        />
      </div>

      {/* Tools Panel */}
      <ToolsPanel 
        isOpen={toolsPanelOpen} 
        onClose={() => setToolsPanelOpen(false)} 
      />

      {/* Agent Settings Modal */}
      <AgentModal 
        isOpen={agentModalOpen}
        onClose={() => setAgentModalOpen(false)}
      />
    </div>
  )
}

function App() {
  return (
    <Router>
      <WSProvider>
        <ChatProvider>
          <MarketplaceProvider>
            <Routes>
              <Route path="/" element={<ChatInterface />} />
              <Route path="/marketplace" element={<MarketplacePanel />} />
            </Routes>
          </MarketplaceProvider>
        </ChatProvider>
      </WSProvider>
    </Router>
  )
}

export default App