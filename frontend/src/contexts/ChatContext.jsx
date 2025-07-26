import { createContext, useContext, useEffect, useState } from 'react'
import { useWS } from './WSContext'

const ChatContext = createContext()

export const useChat = () => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

export const ChatProvider = ({ children }) => {
  // App state
  const [appName, setAppName] = useState('Chat UI')
  const [user, setUser] = useState('Unknown')
  const [models, setModels] = useState([])
  const [tools, setTools] = useState([])
  const [dataSources, setDataSources] = useState([])
  
  // Current selections
  const [currentModel, setCurrentModel] = useState('')
  const [selectedTools, setSelectedTools] = useState(new Set())
  const [selectedDataSources, setSelectedDataSources] = useState(new Set())
  const [onlyRag, setOnlyRag] = useState(true)
  const [toolChoiceRequired, setToolChoiceRequired] = useState(false)
  
  // Agent mode
  const [agentModeEnabled, setAgentModeEnabled] = useState(false)
  const [agentMaxSteps, setAgentMaxSteps] = useState(5)
  const [agentModeAvailable, setAgentModeAvailable] = useState(true)
  const [currentAgentStep, setCurrentAgentStep] = useState(0)
  
  // Chat state
  const [messages, setMessages] = useState([])
  const [isWelcomeVisible, setIsWelcomeVisible] = useState(true)
  const [isThinking, setIsThinking] = useState(false)
  
  // Canvas state
  const [canvasContent, setCanvasContent] = useState('')
  
  const { sendMessage, addMessageHandler } = useWS()

  // Load configuration on mount
  useEffect(() => {
    loadConfig()
  }, [])

  // Load tool selections from localStorage
  useEffect(() => {
    loadToolSelections()
    loadToolChoiceRequired()
  }, [])

  // WebSocket message handler
  useEffect(() => {
    const removeHandler = addMessageHandler(handleWebSocketMessage)
    return removeHandler
  }, [addMessageHandler])

  const loadConfig = async () => {
    try {
      const response = await fetch('/api/config')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const config = await response.json()
      
      setAppName(config.app_name || 'Chat UI')
      setModels(config.models || [])
      setTools(config.tools || [])
      setDataSources(config.data_sources || [])
      setUser(config.user || 'Unknown')
      setAgentModeAvailable(config.agent_mode_available !== false)
      
      // Auto-select first model if available
      if (config.models && config.models.length > 0 && !currentModel) {
        setCurrentModel(config.models[0])
      }
    } catch (error) {
      console.error('Error loading config:', error)
      // Fallback to demo data when backend is not available
      setAppName('Chat UI (Demo)')
      setModels(['gpt-4o', 'gpt-4o-mini'])
      setTools([
        {
          server: 'canvas',
          tools: ['canvas'],
          description: 'Create and display visual content',
          tool_count: 1,
          is_exclusive: false
        }
      ])
      setDataSources(['demo_documents'])
      setUser('Demo User')
      setCurrentModel('gpt-4o')
    }
  }

  const loadToolSelections = () => {
    try {
      const savedSelections = localStorage.getItem('chatui-selected-tools')
      if (savedSelections) {
        const selections = JSON.parse(savedSelections)
        setSelectedTools(new Set(selections))
      } else {
        // Auto-select canvas tool for new users
        setSelectedTools(new Set(['canvas_canvas']))
        saveToolSelections(['canvas_canvas'])
      }
    } catch (error) {
      console.warn('Failed to load tool selections:', error)
      setSelectedTools(new Set())
    }
  }

  const saveToolSelections = (selections = null) => {
    try {
      const selectionsArray = selections || Array.from(selectedTools)
      localStorage.setItem('chatui-selected-tools', JSON.stringify(selectionsArray))
    } catch (error) {
      console.warn('Failed to save tool selections:', error)
    }
  }

  const loadToolChoiceRequired = () => {
    try {
      const saved = localStorage.getItem('chatui-tool-choice-required')
      if (saved !== null) {
        setToolChoiceRequired(JSON.parse(saved))
      }
    } catch (error) {
      console.warn('Failed to load tool choice required setting:', error)
    }
  }

  const saveToolChoiceRequired = (value) => {
    try {
      localStorage.setItem('chatui-tool-choice-required', JSON.stringify(value))
    } catch (error) {
      console.warn('Failed to save tool choice required setting:', error)
    }
  }

  const toggleTool = (toolKey) => {
    const newSelected = new Set(selectedTools)
    if (newSelected.has(toolKey)) {
      newSelected.delete(toolKey)
    } else {
      newSelected.add(toolKey)
    }
    setSelectedTools(newSelected)
    saveToolSelections(Array.from(newSelected))
  }

  const toggleDataSource = (dataSource) => {
    const newSelected = new Set(selectedDataSources)
    if (newSelected.has(dataSource)) {
      newSelected.delete(dataSource)
    } else {
      newSelected.add(dataSource)
    }
    setSelectedDataSources(newSelected)
  }

  const sendChatMessage = (content) => {
    if (!content.trim() || !currentModel) return

    // Hide welcome screen on first message
    if (isWelcomeVisible) {
      setIsWelcomeVisible(false)
    }

    // Add user message
    const userMessage = { role: 'user', content }
    setMessages(prev => [...prev, userMessage])
    setIsThinking(true)

    // Prepare payload
    const payload = {
      type: 'chat',
      content,
      model: currentModel,
      selected_tools: Array.from(selectedTools),
      selected_data_sources: Array.from(selectedDataSources),
      only_rag: onlyRag,
      tool_choice_required: toolChoiceRequired,
      user
    }

    // Add agent mode parameters if available
    if (agentModeAvailable) {
      payload.agent_mode = agentModeEnabled
      payload.agent_max_steps = agentMaxSteps
    }

    sendMessage(payload)
  }

  const handleWebSocketMessage = (data) => {
    try {
      switch (data.type) {
        case 'chat_response':
          setIsThinking(false)
          const assistantMessage = { role: 'assistant', content: data.message }
          setMessages(prev => [...prev, assistantMessage])
          break

        case 'error':
          setIsThinking(false)
          const errorMessage = { role: 'system', content: `Error: ${data.message}` }
          setMessages(prev => [...prev, errorMessage])
          break

        case 'agent_step_update':
          setCurrentAgentStep(data.current_step)
          break

        case 'agent_final_response':
          setIsThinking(false)
          setCurrentAgentStep(0)
          const agentResponse = { 
            role: 'assistant', 
            content: `${data.message}\n\n*Agent completed in ${data.steps_taken} steps*` 
          }
          setMessages(prev => [...prev, agentResponse])
          break

        case 'intermediate_update':
          handleIntermediateUpdate(data)
          break

        default:
          console.warn('Unknown message type:', data.type)
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error, data)
    }
  }

  const handleIntermediateUpdate = (data) => {
    try {
      const updateType = data.update_type
      const updateData = data.data

      switch (updateType) {
        case 'tool_call':
          // Add tool call indicator message
          const toolCallMessage = {
            role: 'system',
            content: `**Tool Call: ${updateData.tool_name}** (${updateData.server_name})`,
            type: 'tool_call',
            tool_call_id: updateData.tool_call_id,
            tool_name: updateData.tool_name,
            server_name: updateData.server_name,
            arguments: updateData.arguments || {},
            status: 'calling'
          }
          setMessages(prev => [...prev, toolCallMessage])
          break

        case 'tool_result':
          // Update tool call message with result
          setMessages(prev => prev.map(msg => {
            if (msg.tool_call_id === updateData.tool_call_id) {
              return {
                ...msg,
                content: `**Tool: ${updateData.tool_name}** - ${updateData.success ? 'Success' : 'Failed'}`,
                status: updateData.success ? 'completed' : 'failed',
                result: updateData.result || updateData.error || null
              }
            }
            return msg
          }))
          break

        case 'canvas_content':
          try {
            if (updateData && updateData.content) {
              // Ensure canvas content is properly typed
              const content = typeof updateData.content === 'string' 
                ? updateData.content 
                : String(updateData.content || '')
              setCanvasContent(content)
            }
          } catch (canvasError) {
            console.error('Error handling canvas content:', canvasError, updateData)
            // Set safe fallback content
            setCanvasContent('Error displaying canvas content')
          }
          break

        default:
          console.warn('Unknown intermediate update type:', updateType)
      }
    } catch (error) {
      console.error('Error handling intermediate update:', error, data)
    }
  }

  const clearChat = () => {
    setMessages([])
    setIsWelcomeVisible(true)
    setCanvasContent('')
  }

  const value = {
    // App state
    appName,
    user,
    models,
    tools,
    dataSources,
    
    // Current selections
    currentModel,
    setCurrentModel,
    selectedTools,
    toggleTool,
    selectedDataSources,
    toggleDataSource,
    onlyRag,
    setOnlyRag,
    toolChoiceRequired,
    setToolChoiceRequired: (value) => {
      setToolChoiceRequired(value)
      saveToolChoiceRequired(value)
    },
    
    // Agent mode
    agentModeEnabled,
    setAgentModeEnabled,
    agentMaxSteps,
    setAgentMaxSteps,
    agentModeAvailable,
    currentAgentStep,
    
    // Chat state
    messages,
    isWelcomeVisible,
    isThinking,
    sendChatMessage,
    clearChat,
    
    // Canvas
    canvasContent,
    setCanvasContent
  }

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}