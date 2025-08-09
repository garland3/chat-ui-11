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
  console.log('🔧 [TOOLS DEBUG] ChatProvider component initialized')
  
  // App state
  const [appName, setAppName] = useState('Chat UI')
  const [user, setUser] = useState('Unknown')
  const [models, setModels] = useState([])
  const [tools, setTools] = useState([])
  const [prompts, setPrompts] = useState([])
  const [dataSources, setDataSources] = useState([])
  
  // Current selections
  const [currentModel, setCurrentModel] = useState('')
  const [selectedTools, setSelectedTools] = useState(new Set())
  const [selectedPrompts, setSelectedPrompts] = useState(new Set())
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
  const [canvasFiles, setCanvasFiles] = useState([])
  const [currentCanvasFileIndex, setCurrentCanvasFileIndex] = useState(0)
  
  // Custom UI state
  const [customUIContent, setCustomUIContent] = useState(null)
  
  // Files state
  const [sessionFiles, setSessionFiles] = useState({
    total_files: 0,
    files: [],
    categories: {
      code: [],
      image: [],
      data: [],
      document: [],
      other: []
    }
  })
  
  // Tagged files for context inclusion
  const [taggedFiles, setTaggedFiles] = useState(new Set())
  
  const { sendMessage, addMessageHandler } = useWS()

  // Helper function to determine canvas file type from filename
  const getFileType = (filename) => {
    const extension = filename.toLowerCase().split('.').pop()
    if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(extension)) {
      return 'image'
    } else if (extension === 'pdf') {
      return 'pdf'  
    } else if (extension === 'html') {
      return 'html'
    } else {
      return 'other'
    }
  }

  // Load configuration on mount
  useEffect(() => {
    loadConfig()
  }, [])

  // Load tool selections from localStorage
  useEffect(() => {
    loadToolSelections()
    loadPromptSelections()
    loadToolChoiceRequired()
    loadAgentModeSettings()
    loadTaggedFiles()
  }, [])

  // WebSocket message handler
  useEffect(() => {
    const removeHandler = addMessageHandler(handleWebSocketMessage)
    return removeHandler
  }, [addMessageHandler])

  // Debug: Track selectedTools changes
  useEffect(() => {
    const selectedToolsList = Array.from(selectedTools)
    console.log('🔧 [TOOLS DEBUG] Selected tools changed:', {
      count: selectedToolsList.length,
      tools: selectedToolsList,
      timestamp: new Date().toLocaleTimeString()
    })
    
    // Also log which server each tool belongs to for easier debugging
    if (selectedToolsList.length > 0) {
      const toolsByServer = {}
      selectedToolsList.forEach(toolKey => {
        const [server, tool] = toolKey.split('_')
        if (!toolsByServer[server]) {
          toolsByServer[server] = []
        }
        toolsByServer[server].push(tool)
      })
      console.log('🔧 [TOOLS DEBUG] Tools by server:', toolsByServer)
    }
  }, [selectedTools])

  const loadConfig = async () => {
    try {
      const response = await fetch('/api/config')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const config = await response.json()
      
      setAppName(config.app_name || 'Chat UI')
      setModels(config.models || [])
      // Process tools to remove duplicate tool names within each server
      const uniqueTools = (config.tools || []).map(toolServer => {
        const uniqueToolNames = new Set(toolServer.tools)
        return {
          ...toolServer,
          tools: Array.from(uniqueToolNames)
        }
      })
      setTools(uniqueTools)
      console.log('🔧 [TOOLS DEBUG] Loaded unique tools:', uniqueTools)
      setPrompts(config.prompts || [])
      console.log('🔧 [PROMPTS DEBUG] Loaded prompts:', config.prompts || [])
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
    console.log('🔧 [TOOLS DEBUG] loadToolSelections called')
    try {
      const savedSelections = localStorage.getItem('chatui-selected-tools')
      if (savedSelections) {
        const selections = JSON.parse(savedSelections)
        console.log('🔧 [TOOLS DEBUG] Loading saved selections from localStorage:', selections)
        setSelectedTools(new Set(selections))
      } else {
        // Auto-select canvas tool for new users
        console.log('🔧 [TOOLS DEBUG] No saved selections, auto-selecting canvas tool')
        setSelectedTools(new Set(['canvas_canvas']))
        saveToolSelections(['canvas_canvas'])
      }
    } catch (error) {
      console.warn('Failed to load tool selections:', error)
      console.log('🔧 [TOOLS DEBUG] Error loading selections, clearing selectedTools')
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

  const loadPromptSelections = () => {
    console.log('🔧 [PROMPTS DEBUG] loadPromptSelections called')
    try {
      const savedSelections = localStorage.getItem('chatui-selected-prompts')
      if (savedSelections) {
        const selections = JSON.parse(savedSelections)
        console.log('🔧 [PROMPTS DEBUG] Loading saved selections from localStorage:', selections)
        setSelectedPrompts(new Set(selections))
      } else {
        console.log('🔧 [PROMPTS DEBUG] No saved selections, starting with empty set')
        setSelectedPrompts(new Set())
      }
    } catch (error) {
      console.warn('Failed to load prompt selections:', error)
      console.log('🔧 [PROMPTS DEBUG] Error loading selections, clearing selectedPrompts')
      setSelectedPrompts(new Set())
    }
  }

  const savePromptSelections = (selections = null) => {
    try {
      const selectionsArray = selections || Array.from(selectedPrompts)
      localStorage.setItem('chatui-selected-prompts', JSON.stringify(selectionsArray))
    } catch (error) {
      console.warn('Failed to save prompt selections:', error)
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

  const loadAgentModeSettings = () => {
    try {
      const savedAgentMode = localStorage.getItem('chatui-agent-mode-enabled')
      if (savedAgentMode !== null) {
        setAgentModeEnabled(JSON.parse(savedAgentMode))
      }
      
      const savedMaxSteps = localStorage.getItem('chatui-agent-max-steps')
      if (savedMaxSteps !== null) {
        setAgentMaxSteps(JSON.parse(savedMaxSteps))
      }
    } catch (error) {
      console.warn('Failed to load agent mode settings:', error)
    }
  }

  const saveAgentModeSettings = (enabled, maxSteps) => {
    try {
      localStorage.setItem('chatui-agent-mode-enabled', JSON.stringify(enabled))
      if (maxSteps !== undefined) {
        localStorage.setItem('chatui-agent-max-steps', JSON.stringify(maxSteps))
      }
    } catch (error) {
      console.warn('Failed to save agent mode settings:', error)
    }
  }

  // Wrapper function that updates state and saves to localStorage
  const updateAgentModeEnabled = (enabled) => {
    setAgentModeEnabled(enabled)
    saveAgentModeSettings(enabled, agentMaxSteps)
  }

  const updateAgentMaxSteps = (steps) => {
    setAgentMaxSteps(steps)
    saveAgentModeSettings(agentModeEnabled, steps)
  }

  const toggleTool = (toolKey) => {
    console.log('🔧 [TOOLS DEBUG] toggleTool called with:', toolKey)
    console.log('🔧 [TOOLS DEBUG] Current selectedTools before toggle:', Array.from(selectedTools))
    
    const newSelected = new Set(selectedTools)
    const wasSelected = newSelected.has(toolKey)
    
    if (wasSelected) {
      newSelected.delete(toolKey)
      console.log('🔧 [TOOLS DEBUG] Removed tool:', toolKey)
    } else {
      newSelected.add(toolKey)
      console.log('🔧 [TOOLS DEBUG] Added tool:', toolKey)
    }
    
    console.log('🔧 [TOOLS DEBUG] New selectedTools after toggle:', Array.from(newSelected))
    setSelectedTools(newSelected)
    saveToolSelections(Array.from(newSelected))
  }

  const selectAllServerTools = (serverName) => {
    console.log('🔧 [TOOLS DEBUG] selectAllServerTools called for server:', serverName)
    
    const serverTools = tools.find(t => t.server === serverName)
    if (!serverTools) return

    const serverToolKeys = serverTools.tools.map(tool => `${serverName}_${tool}`)
    const newSelected = new Set(selectedTools)
    
    // Add all tools from this server (avoiding duplicates is handled by Set)
    serverToolKeys.forEach(key => {
      newSelected.add(key)
      console.log('🔧 [TOOLS DEBUG] Adding tool to selection:', key)
    })
    
    console.log('🔧 [TOOLS DEBUG] New selectedTools after selecting all:', Array.from(newSelected))
    setSelectedTools(newSelected)
    saveToolSelections(Array.from(newSelected))
  }

  const deselectAllServerTools = (serverName) => {
    console.log('🔧 [TOOLS DEBUG] deselectAllServerTools called for server:', serverName)
    
    const serverTools = tools.find(t => t.server === serverName)
    if (!serverTools) return

    const serverToolKeys = serverTools.tools.map(tool => `${serverName}_${tool}`)
    const newSelected = new Set(selectedTools)
    
    // Remove all tools from this server
    serverToolKeys.forEach(key => {
      newSelected.delete(key)
      console.log('🔧 [TOOLS DEBUG] Removing tool from selection:', key)
    })
    
    console.log('🔧 [TOOLS DEBUG] New selectedTools after deselecting all:', Array.from(newSelected))
    setSelectedTools(newSelected)
    saveToolSelections(Array.from(newSelected))
  }

  const togglePrompt = (promptKey) => {
    console.log('🔧 [PROMPTS DEBUG] togglePrompt called with:', promptKey)
    console.log('🔧 [PROMPTS DEBUG] Current selectedPrompts before toggle:', Array.from(selectedPrompts))
    
    const newSelected = new Set(selectedPrompts)
    const wasSelected = newSelected.has(promptKey)
    
    if (wasSelected) {
      newSelected.delete(promptKey)
      console.log('🔧 [PROMPTS DEBUG] Removed prompt:', promptKey)
    } else {
      newSelected.add(promptKey)
      console.log('🔧 [PROMPTS DEBUG] Added prompt:', promptKey)
    }
    
    console.log('🔧 [PROMPTS DEBUG] New selectedPrompts after toggle:', Array.from(newSelected))
    setSelectedPrompts(newSelected)
    savePromptSelections(Array.from(newSelected))
  }

  const selectAllServerPrompts = (serverName) => {
    console.log('🔧 [PROMPTS DEBUG] selectAllServerPrompts called for server:', serverName)
    
    const serverPrompts = prompts.find(p => p.server === serverName)
    if (!serverPrompts) return
    const serverPromptKeys = serverPrompts.prompts.map(prompt => `${serverName}_${prompt.name}`)
    const newSelected = new Set(selectedPrompts)
    
    // Add all prompts from this server
    serverPromptKeys.forEach(key => {
      newSelected.add(key)
      console.log('🔧 [PROMPTS DEBUG] Adding prompt to selection:', key)
    })
    
    console.log('🔧 [PROMPTS DEBUG] New selectedPrompts after selecting all:', Array.from(newSelected))
    setSelectedPrompts(newSelected)
    savePromptSelections(Array.from(newSelected))
  }

  const deselectAllServerPrompts = (serverName) => {
    console.log('🔧 [PROMPTS DEBUG] deselectAllServerPrompts called for server:', serverName)
    
    const serverPrompts = prompts.find(p => p.server === serverName)
    if (!serverPrompts) return
    const serverPromptKeys = serverPrompts.prompts.map(prompt => `${serverName}_${prompt.name}`)
    const newSelected = new Set(selectedPrompts)
    
    // Remove all prompts from this server
    serverPromptKeys.forEach(key => {
      newSelected.delete(key)
      console.log('🔧 [PROMPTS DEBUG] Removing prompt from selection:', key)
    })
    
    console.log('🔧 [PROMPTS DEBUG] New selectedPrompts after deselecting all:', Array.from(newSelected))
    setSelectedPrompts(newSelected)
    savePromptSelections(Array.from(newSelected))
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

  const sendChatMessage = async (content, files = {}) => {
    if (!content.trim() || !currentModel) return

    // Hide welcome screen on first message
    if (isWelcomeVisible) {
      setIsWelcomeVisible(false)
    }

    // Add user message
    const userMessage = { 
      role: 'user', 
      content,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsThinking(true)

    // Debug: Log the tools being sent
    const selectedToolsArray = Array.from(selectedTools)
    console.log('🔧 [TOOLS DEBUG] Sending chat message with tools:', {
      selected_tools: selectedToolsArray,
      count: selectedToolsArray.length,
      timestamp: new Date().toLocaleTimeString(),
      message_preview: content.substring(0, 50) + '...'
    })

    // Include tagged files in the files payload
    const taggedFilesContent = await getTaggedFilesContent()
    const allFiles = { ...files, ...taggedFilesContent }
    
    console.log('📁 [FILES DEBUG] Including files in message:', {
      uploaded_files: Object.keys(files).length,
      tagged_files: Object.keys(taggedFilesContent).length,
      total_files: Object.keys(allFiles).length
    })

    // Prepare payload
    const selectedPromptsArray = Array.from(selectedPrompts)
    const payload = {
      type: 'chat',
      content,
      model: currentModel,
      selected_tools: selectedToolsArray,
      selected_prompts: selectedPromptsArray,
      selected_data_sources: Array.from(selectedDataSources),
      only_rag: onlyRag,
      tool_choice_required: toolChoiceRequired,
      user,
      files: allFiles // Add files to payload including tagged files
    }

    // Add agent mode parameters if available
    if (agentModeAvailable) {
      payload.agent_mode = agentModeEnabled
      payload.agent_max_steps = agentMaxSteps
    }

    console.log('🔧 [TOOLS DEBUG] Full payload being sent:', {
      selected_tools: payload.selected_tools,
      selected_prompts: payload.selected_prompts,
      tool_choice_required: payload.tool_choice_required,
      model: payload.model
    })

    sendMessage(payload)
  }

  const handleWebSocketMessage = (data) => {
    console.log('🔧 [TOOLS DEBUG] WebSocket message received:', data.type, data)
    try {
      switch (data.type) {
        case 'chat_response':
          setIsThinking(false)
          const assistantMessage = { 
            role: 'assistant', 
            content: data.message,
            timestamp: new Date().toISOString()
          }
          setMessages(prev => [...prev, assistantMessage])
          break

        case 'error':
          setIsThinking(false)
          const errorMessage = { 
            role: 'system', 
            content: `Error: ${data.message}`,
            timestamp: new Date().toISOString()
          }
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
            content: `${data.message}\n\n*Agent completed in ${data.steps_taken} steps*`,
            timestamp: new Date().toISOString()
          }
          setMessages(prev => [...prev, agentResponse])
          break

        case 'intermediate_update':
          handleIntermediateUpdate(data)
          break

        default:
          // Check if it's an agent update wrapped in intermediate_update
          if (data.update_type === 'agent_update' && data.data) {
            handleAgentUpdate(data.data)
          } else {
            console.warn('Unknown message type:', data.type)
          }
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error, data)
    }
  }

  const handleAgentUpdate = (data) => {
    console.log('Agent update received:', data.type, data)
    try {
      switch (data.type) {
        case 'agent_start':
          // Add a system message indicating agent mode started
          const startMessage = {
            role: 'system',
            content: `**Agent Mode Started** - ${data.message}`,
            type: 'agent_status',
            timestamp: new Date().toISOString()
          }
          setMessages(prev => [...prev, startMessage])
          break

        case 'agent_turn_start':
          // Update current step
          setCurrentAgentStep(data.turn)
          break

        case 'agent_llm_call':
          // Could show that LLM is being called
          console.log(`Agent step ${data.step}: Calling LLM with ${data.tool_count} tools`)
          break

        case 'agent_tool_calls_start':
          // Could show tool execution starting
          console.log(`Agent step ${data.step}: Starting ${data.tool_count} tool calls`)
          break

        case 'agent_tool_call':
          // Add tool call message for each individual tool
          const toolCallMessage = {
            role: 'system',
            content: `**Agent Tool Call**: ${data.function_name}`,
            type: 'tool_call', // Use the same type as regular tool calls for consistent UI
            tool_call_id: `agent_${data.step}_${data.tool_index}`,
            tool_name: data.function_name,
            server_name: 'agent_step',
            arguments: data.arguments,
            step: data.step,
            status: 'calling',
            timestamp: new Date().toISOString(),
            agent_mode: true
          }
          setMessages(prev => [...prev, toolCallMessage])
          break

        case 'agent_tool_results':
          // Update any recent tool call messages with completion status
          console.log(`Agent step ${data.step}: Received ${data.results_count} tool results`)
          break

        case 'agent_completion_detected':
          const completionMessage = {
            role: 'system',
            content: `**Agent Completion** - ${data.message}`,
            type: 'agent_status',
            timestamp: new Date().toISOString()
          }
          setMessages(prev => [...prev, completionMessage])
          break

        case 'agent_completion':
          setCurrentAgentStep(0)
          setIsThinking(false)
          const finalMessage = {
            role: 'assistant',
            content: `${data.final_response}\n\n*Agent completed task in ${data.total_steps} steps*`,
            timestamp: new Date().toISOString()
          }
          setMessages(prev => [...prev, finalMessage])
          break

        case 'agent_step_complete':
          console.log(`Agent step ${data.turn}: Completed`)
          break

        case 'agent_error':
          const errorMessage = {
            role: 'system',
            content: `**Agent Error** (Step ${data.turn}): ${data.message}`,
            type: 'agent_error',
            timestamp: new Date().toISOString()
          }
          setMessages(prev => [...prev, errorMessage])
          setIsThinking(false)
          setCurrentAgentStep(0)
          break

        case 'agent_max_steps':
          const maxStepsMessage = {
            role: 'system',
            content: `**Agent Max Steps Reached** - ${data.message}`,
            type: 'agent_status',
            timestamp: new Date().toISOString()
          }
          setMessages(prev => [...prev, maxStepsMessage])
          setIsThinking(false)
          setCurrentAgentStep(0)
          break

        case 'agent_warning':
          console.warn(`Agent warning: ${data.message}`)
          break

        default:
          console.log('Unknown agent update type:', data.type, data)
      }
    } catch (error) {
      console.error('Error handling agent update:', error, data)
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
            arguments: updateData.parameters || updateData.arguments || {},
            status: 'calling',
            timestamp: new Date().toISOString(),
            agent_mode: updateData.agent_mode || false  // Include agent mode flag
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

        case 'canvas_files':
          try {
            if (updateData && updateData.files && Array.isArray(updateData.files)) {
              console.log('Received canvas files:', updateData.files.length, 'files from', updateData.server_name, updateData.tool_name)
              setCanvasFiles(updateData.files)
              setCurrentCanvasFileIndex(0) // Start with first file
              // Clear old canvas content and custom UI when files are provided
              setCanvasContent('')
              setCustomUIContent(null)
            }
          } catch (filesError) {
            console.error('Error handling canvas files:', filesError, updateData)
            setCanvasFiles([])
          }
          break

        case 'custom_ui':
          try {
            if (updateData && updateData.type === 'html_injection' && updateData.content) {
              console.log('Received custom UI content from MCP server:', updateData.server_name, updateData.tool_name)
              setCustomUIContent({
                type: 'html_injection',
                content: updateData.content,
                toolName: updateData.tool_name,
                serverName: updateData.server_name,
                timestamp: Date.now()
              })
            }
          } catch (customUIError) {
            console.error('Error handling custom UI content:', customUIError, updateData)
            setCustomUIContent({
              type: 'error',
              content: 'Error processing custom UI content',
              timestamp: Date.now()
            })
          }
          break

        case 'files_update':
          try {
            console.log('Received files update:', updateData)
            if (updateData) {
              setSessionFiles(prev => {
                // Auto-open canvas for viewable files
                if (updateData.files && updateData.files.length > 0) {
                  // Find new viewable files (images, PDFs, HTML)
                  const viewableFiles = updateData.files.filter(file => {
                    const extension = file.filename.toLowerCase().split('.').pop()
                    return ['png', 'jpg', 'jpeg', 'gif', 'svg', 'pdf', 'html'].includes(extension)
                  })
                  
                  if (viewableFiles.length > 0) {
                    console.log('Auto-opening canvas for viewable files:', viewableFiles.length, 'files')
                    // Set the viewable files as canvas files
                    const canvasFiles = viewableFiles.map(file => ({
                      ...file,
                      type: getFileType(file.filename)
                    }))
                    setCanvasFiles(canvasFiles)
                    setCurrentCanvasFileIndex(0)
                    // Clear other canvas content
                    setCanvasContent('')
                    setCustomUIContent(null)
                  }
                }
                return updateData
              })
            }
          } catch (filesError) {
            console.error('Error handling files update:', filesError, updateData)
          }
          break

        case 'file_download':
          try {
            console.log('Received file download:', updateData)
            if (updateData && updateData.filename && updateData.content_base64) {
              // Trigger actual file download
              triggerFileDownload(updateData.filename, updateData.content_base64)
            }
          } catch (downloadError) {
            console.error('Error handling file download:', downloadError, updateData)
          }
          break

        default:
          console.warn('Unknown intermediate update type:', updateType)
      }
    } catch (error) {
      console.error('Error handling intermediate update:', error, data)
    }
  }

  const triggerFileDownload = (filename, base64Content) => {
    try {
      // Convert base64 to blob
      const byteCharacters = atob(base64Content)
      const byteNumbers = new Array(byteCharacters.length)
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i)
      }
      const byteArray = new Uint8Array(byteNumbers)
      
      // Determine MIME type based on file extension
      const extension = filename.split('.').pop()?.toLowerCase()
      let mimeType = 'application/octet-stream'
      
      const mimeTypes = {
        'pdf': 'application/pdf',
        'txt': 'text/plain',
        'json': 'application/json',
        'csv': 'text/csv',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'py': 'text/x-python',
        'js': 'text/javascript',
        'html': 'text/html',
        'css': 'text/css',
        'xml': 'application/xml'
      }
      
      if (extension && mimeTypes[extension]) {
        mimeType = mimeTypes[extension]
      }
      
      const blob = new Blob([byteArray], { type: mimeType })
      
      // Create download link and trigger download
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Clean up
      setTimeout(() => URL.revokeObjectURL(url), 100)
      
      console.log(`Downloaded file: ${filename}`)
      
    } catch (error) {
      console.error('Error downloading file:', error)
      alert('Failed to download file. Please try again.')
    }
  }

  const clearChat = () => {
    setMessages([])
    setIsWelcomeVisible(true)
    setCanvasContent('')
    setCustomUIContent(null)
    setSessionFiles({
      total_files: 0,
      files: [],
      categories: {
        code: [],
        image: [],
        data: [],
        document: [],
        other: []
      }
    })
  }

  const downloadFile = (filename) => {
    try {
      // Find the file in session files
      const file = sessionFiles.files.find(f => f.filename === filename)
      if (!file) {
        console.error('File not found:', filename)
        return
      }

      // Send WebSocket message to request file download
      sendMessage({
        type: 'download_file',
        filename: filename
      })
      
    } catch (error) {
      console.error('Error downloading file:', error)
    }
  }

  const deleteFile = (filename) => {
    try {
      if (confirm(`Are you sure you want to delete ${filename}?`)) {
        // TODO: Send WebSocket message to delete file from session
        console.log('Would delete file:', filename)
        
        // For now, just remove from local state
        setSessionFiles(prev => {
          const newFiles = prev.files.filter(f => f.filename !== filename)
          const newCategories = {}
          
          // Rebuild categories
          Object.keys(prev.categories).forEach(category => {
            newCategories[category] = newFiles.filter(f => f.type === category)
          })
          
          return {
            total_files: newFiles.length,
            files: newFiles,
            categories: newCategories
          }
        })
      }
    } catch (error) {
      console.error('Error deleting file:', error)
    }
  }

  const toggleFileTag = (filename) => {
    setTaggedFiles(prev => {
      const newTagged = new Set(prev)
      if (newTagged.has(filename)) {
        newTagged.delete(filename)
      } else {
        newTagged.add(filename)
      }
      
      // Save to localStorage
      localStorage.setItem('chatui-tagged-files', JSON.stringify(Array.from(newTagged)))
      
      console.log(`File "${filename}" ${newTagged.has(filename) ? 'tagged' : 'untagged'} for context`)
      return newTagged
    })
  }

  const clearTaggedFiles = () => {
    setTaggedFiles(new Set())
    localStorage.removeItem('chatui-tagged-files')
    console.log('Cleared all tagged files')
  }

  const loadTaggedFiles = () => {
    try {
      const saved = localStorage.getItem('chatui-tagged-files')
      if (saved) {
        const taggedArray = JSON.parse(saved)
        setTaggedFiles(new Set(taggedArray))
        console.log('Loaded tagged files from localStorage:', taggedArray)
      }
    } catch (error) {
      console.error('Error loading tagged files:', error)
    }
  }

  const getTaggedFilesContent = async () => {
    const taggedArray = Array.from(taggedFiles)
    const fileContents = {}
    
    for (const filename of taggedArray) {
      // Check if file exists in session files
      const fileExists = sessionFiles.files.some(f => f.filename === filename)
      if (fileExists) {
        fileContents[filename] = `[File: ${filename} - included for context]`
      }
    }
    
    return fileContents
  }

  const clearToolsAndPrompts = () => {
    // Clear selected tools and prompts
    setSelectedTools(new Set())
    setSelectedPrompts(new Set())
    
    // Clear from localStorage
    localStorage.removeItem('chatui-selected-tools')
    localStorage.removeItem('chatui-selected-prompts')
    
    console.log('🔧 [TOOLS DEBUG] Cleared all tool and prompt selections from memory')
  }

  const downloadChat = () => {
    if (messages.length === 0) {
      alert('No chat history to download')
      return
    }

    // Format the chat data
    const chatData = {
      metadata: {
        exportDate: new Date().toISOString(),
        appName,
        user,
        model: currentModel,
        selectedTools: Array.from(selectedTools),
        selectedDataSources: Array.from(selectedDataSources),
        onlyRag,
        toolChoiceRequired,
        agentModeEnabled,
        agentMaxSteps,
        messageCount: messages.length,
        exportVersion: '1.0'
      },
      conversation: messages.map((message, index) => {
        const baseMessage = {
          index: index + 1,
          role: message.role,
          content: message.content,
          timestamp: message.timestamp || new Date().toISOString()
        }

        // Add tool-specific data if it's a tool call/result
        if (message.type === 'tool_call') {
          baseMessage.messageType = 'tool_call'
          baseMessage.toolDetails = {
            name: message.tool_name,
            server: message.server_name,
            callId: message.tool_call_id,
            arguments: message.arguments,
            status: message.status
          }
          if (message.result) {
            baseMessage.toolDetails.result = message.result
          }
        } else if (message.role === 'system') {
          baseMessage.messageType = 'system'
        } else if (message.role === 'assistant') {
          baseMessage.messageType = 'assistant_response'
        } else if (message.role === 'user') {
          baseMessage.messageType = 'user_input'
        }

        return baseMessage
      }),
      canvasContent: canvasContent || null,
      sessionSummary: {
        totalMessages: messages.length,
        userMessages: messages.filter(m => m.role === 'user').length,
        assistantMessages: messages.filter(m => m.role === 'assistant').length,
        systemMessages: messages.filter(m => m.role === 'system').length,
        toolCalls: messages.filter(m => m.type === 'tool_call').length
      }
    }

    // Create and download the file
    const dataStr = JSON.stringify(chatData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    link.download = `chat-export-${timestamp}.json`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const downloadChatAsText = () => {
    if (messages.length === 0) {
      alert('No chat history to download')
      return
    }

    // Format the chat as readable text
    let textContent = `Chat Export - ${appName}\n`
    textContent += `Date: ${new Date().toLocaleString()}\n`
    textContent += `User: ${user}\n`
    textContent += `Model: ${currentModel}\n`
    textContent += `Selected Tools: ${Array.from(selectedTools).join(', ') || 'None'}\n`
    textContent += `Selected Data Sources: ${Array.from(selectedDataSources).join(', ') || 'None'}\n`
    textContent += `Agent Mode: ${agentModeEnabled ? 'Enabled' : 'Disabled'}\n`
    textContent += `\n${'='.repeat(50)}\n\n`

    messages.forEach((message, index) => {
      const timestamp = message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : 'Unknown time'
      
      if (message.role === 'user') {
        textContent += `[${timestamp}] USER:\n${message.content}\n\n`
      } else if (message.role === 'assistant') {
        textContent += `[${timestamp}] ASSISTANT:\n${message.content}\n\n`
      } else if (message.role === 'system' && message.type === 'tool_call') {
        textContent += `[${timestamp}] TOOL CALL - ${message.tool_name} (${message.server_name}):\n`
        if (message.arguments && Object.keys(message.arguments).length > 0) {
          textContent += `Arguments: ${JSON.stringify(message.arguments, null, 2)}\n`
        }
        textContent += `Status: ${message.status}\n`
        if (message.result) {
          textContent += `Result: ${typeof message.result === 'string' ? message.result : JSON.stringify(message.result, null, 2)}\n`
        }
        textContent += '\n'
      } else if (message.role === 'system') {
        textContent += `[${timestamp}] SYSTEM:\n${message.content}\n\n`
      }
    })

    if (canvasContent) {
      textContent += `${'='.repeat(50)}\nCANVAS CONTENT:\n${canvasContent}\n`
    }

    // Create and download the file
    const dataBlob = new Blob([textContent], { type: 'text/plain' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    link.download = `chat-export-${timestamp}.txt`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const value = {
    // App state
    appName,
    user,
    models,
    tools,
    prompts,
    dataSources,
    
    // Current selections
    currentModel,
    setCurrentModel,
    selectedTools,
    toggleTool,
    selectAllServerTools,
    deselectAllServerTools,
    selectedPrompts,
    togglePrompt,
    selectAllServerPrompts,
    deselectAllServerPrompts,
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
    setAgentModeEnabled: updateAgentModeEnabled,
    agentMaxSteps,
    setAgentMaxSteps: updateAgentMaxSteps,
    agentModeAvailable,
    currentAgentStep,
    
    // Chat state
    messages,
    isWelcomeVisible,
    isThinking,
    sendChatMessage,
    clearChat,
    clearToolsAndPrompts,
    downloadChat,
    downloadChatAsText,
    
    // Canvas
    canvasContent,
    setCanvasContent,
    canvasFiles,
    setCanvasFiles,
    currentCanvasFileIndex,
    setCurrentCanvasFileIndex,
    
    // Custom UI
    customUIContent,
    setCustomUIContent,
    
    // Files
    sessionFiles,
    downloadFile,
    deleteFile,
    
    // File tagging
    taggedFiles,
    toggleFileTag,
    clearTaggedFiles
  }

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}
