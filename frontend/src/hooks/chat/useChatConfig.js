import { useEffect, useState } from 'react'
import { useWS } from '../../contexts/WSContext'

const DEFAULT_FEATURES = {
  workspaces: false,
  rag: false,
  tools: false,
  marketplace: false,
  files_panel: false,
  chat_history: false
}

export function useChatConfig() {
  const { config, configLoaded } = useWS()
  const [appName, setAppName] = useState('Chat UI')
  const [user, setUser] = useState('Unknown')
  const [models, setModels] = useState([])
  const [tools, setTools] = useState([])
  const [prompts, setPrompts] = useState([])
  const [dataSources, setDataSources] = useState([])
  const [features, setFeatures] = useState(DEFAULT_FEATURES)
  // Load saved model from localStorage
  const [currentModel, setCurrentModel] = useState(() => {
    try {
      return localStorage.getItem('chatui-current-model') || ''
    } catch {
      return ''
    }
  })
  const [onlyRag, setOnlyRag] = useState(false)
  const [agentModeAvailable, setAgentModeAvailable] = useState(false)
  const [isInAdminGroup, setIsInAdminGroup] = useState(false)

  useEffect(() => {
    if (configLoaded && config) {
      setAppName(config.app_name || 'Chat UI')
      setModels(config.models || [])
      const uniqueTools = (config.tools || []).map(server => ({
        ...server,
        tools: Array.from(new Set(server.tools))
      }))
      setTools(uniqueTools)
      setPrompts(config.prompts || [])
      setDataSources(config.data_sources || [])
      setUser(config.user || 'Unknown')
      setFeatures({ ...DEFAULT_FEATURES, ...(config.features || {}) })
      // Agent mode availability flag from backend
      setAgentModeAvailable(!!config.agent_mode_available)
      // Admin group membership flag from backend
      setIsInAdminGroup(!!config.is_in_admin_group)
      // Set default model if none saved and models available
      if (!currentModel && config.models?.length) {
        const defaultModel = config.models[0]
        setCurrentModel(defaultModel)
        try {
          localStorage.setItem('chatui-current-model', defaultModel)
        } catch (e) {
          console.warn('Failed to save current model to localStorage:', e)
        }
      }
      // Validate saved model is still available
      else if (currentModel && config.models?.length && !config.models.includes(currentModel)) {
        const defaultModel = config.models[0]
        setCurrentModel(defaultModel)
        try {
          localStorage.setItem('chatui-current-model', defaultModel)
        } catch (e) {
          console.warn('Failed to save current model to localStorage:', e)
        }
      }
    } else if (configLoaded && !config) {
      // Fallback demo data when config is loaded but empty (error case)
      setAppName('Chat UI (Demo)')
      setModels(['gpt-4o', 'gpt-4o-mini'])
      setTools([{ server: 'canvas', tools: ['canvas'], description: 'Create and display visual content', tool_count: 1, is_exclusive: false }])
      setDataSources(['demo_documents'])
      setUser('Demo User')
      // Set demo model if no saved model
      if (!currentModel) {
        setCurrentModel('gpt-4o')
        try {
          localStorage.setItem('chatui-current-model', 'gpt-4o')
        } catch (e) {
          console.warn('Failed to save current model to localStorage:', e)
        }
      }
      setAgentModeAvailable(true)
    }
  }, [config, configLoaded, currentModel])

  return {
    appName,
    user,
    models,
    tools,
    prompts,
    dataSources,
    features,
    setFeatures,
    currentModel,
    setCurrentModel: (model) => {
      setCurrentModel(model)
      try {
        localStorage.setItem('chatui-current-model', model)
      } catch (e) {
        console.warn('Failed to save current model to localStorage:', e)
      }
    },
    onlyRag,
    setOnlyRag,
    agentModeAvailable,
    isInAdminGroup
  }
}
