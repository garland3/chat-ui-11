import { useState } from 'react'
import { useChat } from '../contexts/ChatContext'
import { useWS } from '../contexts/WSContext'
import { Menu, ChevronDown, Settings, Bot } from 'lucide-react'

const Header = ({ onToggleRag, onToggleTools, onToggleAgent }) => {
  const { appName, user, models, currentModel, setCurrentModel, agentModeAvailable } = useChat()
  const { connectionStatus, isConnected } = useWS()
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const handleModelSelect = (model) => {
    setCurrentModel(model)
    setDropdownOpen(false)
  }

  return (
    <header className="flex items-center justify-between p-4 bg-gray-800 border-b border-gray-700">
      {/* Left section */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleRag}
          className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
          title="Toggle Data Sources"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Center section */}
      <h1 className="text-xl font-semibold text-gray-100">{appName}</h1>

      {/* Right section */}
      <div className="flex items-center gap-4">
        {/* Model Selection Dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors min-w-40"
          >
            <span className="text-sm text-gray-200">
              {currentModel || 'Select a model...'}
            </span>
            <ChevronDown className="w-4 h-4" />
          </button>
          
          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-gray-800 border border-gray-600 rounded-lg shadow-lg z-50">
              {models.length === 0 ? (
                <div className="px-4 py-2 text-gray-400 text-sm">No models available</div>
              ) : (
                models.map(model => (
                  <button
                    key={model}
                    onClick={() => handleModelSelect(model)}
                    className="w-full text-left px-4 py-2 text-sm text-gray-200 hover:bg-gray-700 first:rounded-t-lg last:rounded-b-lg"
                  >
                    {model}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* User Info */}
        <div className="text-sm text-gray-300">
          {user}
        </div>

        {/* Agent Settings Button */}
        {agentModeAvailable && (
          <button
            onClick={onToggleAgent}
            className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
            title="Agent Settings"
          >
            <Bot className="w-5 h-5" />
          </button>
        )}

        {/* Tools Panel Toggle */}
        <button
          onClick={onToggleTools}
          className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
          title="Toggle Tools"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>

      {/* Connection Status */}
      <div className="absolute bottom-4 right-4 flex items-center gap-2 text-xs">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-gray-400">{connectionStatus}</span>
      </div>

      {/* Close dropdown when clicking outside */}
      {dropdownOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setDropdownOpen(false)}
        />
      )}
    </header>
  )
}

export default Header