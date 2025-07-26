import { useState, useEffect } from 'react'
import { ChatProvider } from './contexts/ChatContext'
import { WSProvider } from './contexts/WSContext'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import ToolsPanel from './components/ToolsPanel'
import RagPanel from './components/RagPanel'
import CanvasPanel from './components/CanvasPanel'
import AgentModal from './components/AgentModal'

function App() {
  const [toolsPanelOpen, setToolsPanelOpen] = useState(false)
  const [ragPanelOpen, setRagPanelOpen] = useState(false)
  const [canvasPanelOpen, setCanvasPanelOpen] = useState(false)
  const [agentModalOpen, setAgentModalOpen] = useState(false)

  return (
    <WSProvider>
      <ChatProvider>
        <div className="flex h-screen w-full bg-gray-900 text-gray-200">
          {/* RAG Data Sources Panel */}
          <RagPanel 
            isOpen={ragPanelOpen} 
            onClose={() => setRagPanelOpen(false)} 
          />

          {/* Main Content Area */}
          <div className="flex flex-col flex-1 relative">
            {/* Canvas Panel */}
            <CanvasPanel 
              isOpen={canvasPanelOpen}
              onClose={() => setCanvasPanelOpen(false)}
            />

            {/* Header */}
            <Header 
              onToggleRag={() => setRagPanelOpen(!ragPanelOpen)}
              onToggleTools={() => setToolsPanelOpen(!toolsPanelOpen)}
              onToggleAgent={() => setAgentModalOpen(!agentModalOpen)}
            />

            {/* Chat Area */}
            <ChatArea canvasPanelOpen={canvasPanelOpen} />
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
      </ChatProvider>
    </WSProvider>
  )
}

export default App