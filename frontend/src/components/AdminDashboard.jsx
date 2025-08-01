import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, Settings, Database, FileText, Activity, 
  Download, Save, X, Check, RefreshCw, Shield,
  MessageSquare, Heart, RotateCcw, Eye
} from 'lucide-react'

const AdminDashboard = () => {
  const navigate = useNavigate()
  const [currentUser, setCurrentUser] = useState('Loading...')
  const [systemStatus, setSystemStatus] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalData, setModalData] = useState({})
  const [currentEndpoint, setCurrentEndpoint] = useState(null)
  const [notifications, setNotifications] = useState([])

  const addNotification = (message, type = 'info') => {
    const id = Date.now()
    const notification = { id, message, type }
    setNotifications(prev => [...prev, notification])
    
    // Auto-remove after 5 seconds for success/info, 8 seconds for errors
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id))
    }, type === 'error' ? 8000 : 5000)
  }

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const loadSystemStatus = async () => {
    try {
      const response = await fetch('/admin/system-status')
      const data = await response.json()
      setSystemStatus(data)
    } catch (err) {
      console.error('Error loading system status:', err)
    }
  }

  const loadDashboard = useCallback(async () => {
    try {
      // Check admin access
      const response = await fetch('/admin/')
      if (!response.ok) {
        if (response.status === 403) {
          setError('Access Denied: You need admin privileges to access this page.')
          return
        }
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      setCurrentUser(data.user)
      
      // Load system status
      await loadSystemStatus()
      setLoading(false)
      
    } catch (err) {
      console.error('Error loading dashboard:', err)
      setError('Error loading admin dashboard: ' + err.message)
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  const openModal = (title, content, endpoint = null) => {
    setModalData({ title, content })
    setCurrentEndpoint(endpoint)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setCurrentEndpoint(null)
  }

  const manageBanners = async () => {
    try {
      const response = await fetch('/admin/banners')
      const data = await response.json()
      
      setCurrentEndpoint('banners')
      
      openModal('Manage Banner Messages', {
        type: 'textarea',
        value: data.messages.join('\n'),
        description: 'These messages will be displayed at the top of the chat interface.'
      }, 'banners')
    } catch (err) {
      addNotification('Error loading banner configuration: ' + err.message, 'error')
    }
  }

  const manageMCP = async () => {
    try {
      const response = await fetch('/admin/mcp-config')
      const data = await response.json()
      
      setCurrentEndpoint('mcp-config')
      
      openModal('Edit MCP Configuration', {
        type: 'textarea',
        value: data.content,
        description: 'Configure MCP servers and their properties. Changes require application restart.'
      }, 'mcp-config')
    } catch (err) {
      addNotification('Error loading MCP configuration: ' + err.message, 'error')
    }
  }

  const manageLLM = async () => {
    try {
      const response = await fetch('/admin/llm-config')
      const data = await response.json()
      
      setCurrentEndpoint('llm-config')
      
      openModal('Edit LLM Configuration', {
        type: 'textarea',
        value: data.content,
        description: 'Configure language models and their endpoints. Changes take effect immediately.'
      }, 'llm-config')
    } catch (err) {
      addNotification('Error loading LLM configuration: ' + err.message, 'error')
    }
  }

  const manageHelp = async () => {
    try {
      const response = await fetch('/admin/help-config')
      const data = await response.json()
      
      setCurrentEndpoint('help-config')
      
      openModal('Edit Help Configuration', {
        type: 'textarea',
        value: data.content,
        description: 'Configure help documentation structure and content.'
      }, 'help-config')
    } catch (err) {
      addNotification('Error loading help configuration: ' + err.message, 'error')
    }
  }

  const viewLogs = async () => {
    try {
      const response = await fetch('/admin/logs?lines=500')
      const data = await response.json()
      
      openModal('Application Logs', {
        type: 'logs',
        content: data.content || 'No log content available',
        lines: data.lines,
        totalLines: data.total_lines,
        readonly: true
      })
    } catch (err) {
      addNotification('Error loading logs: ' + err.message, 'error')
    }
  }

  const downloadLogs = () => {
    try {
      const link = document.createElement('a')
      link.href = '/admin/logs/download'
      link.download = `app_log_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.log`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      addNotification('Log download started', 'success')
    } catch (err) {
      addNotification('Error downloading logs: ' + err.message, 'error')
    }
  }

  const checkHealth = async () => {
    try {
      const response = await fetch('/admin/system-status')
      const data = await response.json()
      
      openModal('System Health Status', {
        type: 'health',
        overallStatus: data.overall_status,
        components: data.components,
        readonly: true
      })
    } catch (err) {
      addNotification('Error checking system health: ' + err.message, 'error')
    }
  }

  const triggerHealthCheck = async () => {
    try {
      const response = await fetch('/admin/trigger-health-check', { method: 'POST' })
      const data = await response.json()
      
      if (data.summary) {
        addNotification(`Health check completed: ${data.summary.healthy_count}/${data.summary.total_count} servers healthy`, 'success')
      } else {
        addNotification('Health check triggered: ' + data.message, 'success')
      }
      
      setTimeout(loadSystemStatus, 2000)
    } catch (err) {
      addNotification('Error triggering health check: ' + err.message, 'error')
    }
  }

  const viewMCPHealth = async () => {
    try {
      const response = await fetch('/admin/mcp-health')
      const data = await response.json()
      
      openModal('MCP Server Health Status', {
        type: 'mcp-health',
        healthSummary: data.health_summary,
        readonly: true
      })
    } catch (err) {
      addNotification('Error getting MCP health status: ' + err.message, 'error')
    }
  }

  const reloadConfiguration = async () => {
    try {
      const response = await fetch('/admin/reload-config', { method: 'POST' })
      const data = await response.json()
      
      if (data.validation_status) {
        const validCount = Object.values(data.validation_status).filter(v => v).length
        const totalCount = Object.keys(data.validation_status).length
        addNotification(`Configuration reloaded: ${validCount}/${totalCount} configs valid. ${data.llm_models_count} LLM models, ${data.mcp_servers_count} MCP servers.`, 'success')
      } else {
        addNotification('Configuration reloaded: ' + data.message, 'success')
      }
      
      setTimeout(loadSystemStatus, 1000)
    } catch (err) {
      addNotification('Error reloading configuration: ' + err.message, 'error')
    }
  }

  const saveConfig = async (content) => {
    if (!currentEndpoint) return
    
    try {
      let payload
      if (currentEndpoint === 'banners') {
        const messages = content.split('\n').map(line => line.trim()).filter(line => line)
        payload = { messages }
      } else {
        const fileType = currentEndpoint.includes('json') ? 'json' : 
                       currentEndpoint.includes('yml') || currentEndpoint.includes('yaml') ? 'yaml' : 'text'
        payload = { content, file_type: fileType }
      }
      
      const response = await fetch(`/admin/${currentEndpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || `HTTP ${response.status}`)
      }
      
      const result = await response.json()
      addNotification('Configuration saved successfully: ' + result.message, 'success')
      
      await loadSystemStatus()
    } catch (err) {
      addNotification('Error saving configuration: ' + err.message, 'error')
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-400 bg-green-900/20'
      case 'warning': return 'text-yellow-400 bg-yellow-900/20'
      case 'error': return 'text-red-400 bg-red-900/20'
      default: return 'text-gray-400 bg-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-gray-200 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p>Loading admin dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-gray-200 flex items-center justify-center">
        <div className="text-center max-w-md">
          <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Access Denied</h2>
          <p className="text-gray-400 mb-6">{error}</p>
          <button 
            onClick={() => navigate('/')}
            className="flex items-center gap-2 mx-auto px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Chat
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 overflow-y-auto">
      <div className="w-full mx-auto p-6">
        {/* Header */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold">Chat UI Admin Dashboard</h1>
            <button 
              onClick={() => navigate('/')}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Chat
            </button>
          </div>
          <p className="text-gray-400">Logged in as: {currentUser}</p>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Banner Messages */}
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <MessageSquare className="w-6 h-6 text-blue-400" />
              <h2 className="text-lg font-semibold">Banner Messages</h2>
            </div>
            <p className="text-gray-400 mb-4">Manage messages displayed at the top of the chat interface.</p>
            <div className={`px-3 py-1 rounded text-sm font-medium mb-4 ${getStatusColor('healthy')}`}>
              Ready
            </div>
            <button 
              onClick={manageBanners}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Manage Banners
            </button>
          </div>

          {/* MCP Configuration */}
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Settings className="w-6 h-6 text-purple-400" />
              <h2 className="text-lg font-semibold">MCP Configuration</h2>
            </div>
            <p className="text-gray-400 mb-4">Configure MCP servers and their settings.</p>
            <div className={`px-3 py-1 rounded text-sm font-medium mb-4 ${getStatusColor(systemStatus.overall_status || 'healthy')}`}>
              {systemStatus.overall_status || 'Ready'}
            </div>
            <button 
              onClick={manageMCP}
              className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
            >
              Edit MCP Config
            </button>
          </div>

          {/* LLM Configuration */}
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Database className="w-6 h-6 text-green-400" />
              <h2 className="text-lg font-semibold">LLM Configuration</h2>
            </div>
            <p className="text-gray-400 mb-4">Manage language model settings and endpoints.</p>
            <div className={`px-3 py-1 rounded text-sm font-medium mb-4 ${getStatusColor('healthy')}`}>
              Ready
            </div>
            <button 
              onClick={manageLLM}
              className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
            >
              Edit LLM Config
            </button>
          </div>

          {/* Help Configuration */}
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <FileText className="w-6 h-6 text-yellow-400" />
              <h2 className="text-lg font-semibold">Help Configuration</h2>
            </div>
            <p className="text-gray-400 mb-4">Update help documentation and user guides.</p>
            <div className={`px-3 py-1 rounded text-sm font-medium mb-4 ${getStatusColor('healthy')}`}>
              Ready
            </div>
            <button 
              onClick={manageHelp}
              className="w-full px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg transition-colors"
            >
              Edit Help Config
            </button>
          </div>

          {/* System Logs */}
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Eye className="w-6 h-6 text-cyan-400" />
              <h2 className="text-lg font-semibold">System Logs</h2>
            </div>
            <p className="text-gray-400 mb-4">View application logs and system information.</p>
            <div className={`px-3 py-1 rounded text-sm font-medium mb-4 ${getStatusColor('healthy')}`}>
              Ready
            </div>
            <button 
              onClick={viewLogs}
              className="w-full px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors"
            >
              View Logs
            </button>
          </div>

          {/* System Health */}
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Activity className="w-6 h-6 text-orange-400" />
              <h2 className="text-lg font-semibold">System Health</h2>
            </div>
            <p className="text-gray-400 mb-4">Monitor overall system status and health checks.</p>
            <div className={`px-3 py-1 rounded text-sm font-medium mb-4 ${getStatusColor(systemStatus.overall_status || 'healthy')}`}>
              {systemStatus.overall_status || 'Ready'}
            </div>
            <div className="space-y-2">
              <button 
                onClick={checkHealth}
                className="w-full px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg transition-colors"
              >
                Check Health
              </button>
              <button 
                onClick={triggerHealthCheck}
                className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors"
              >
                Trigger Health Check
              </button>
              <button 
                onClick={viewMCPHealth}
                className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors"
              >
                MCP Server Health
              </button>
            </div>
          </div>

          {/* Configuration Management */}
          <div className="bg-gray-800 rounded-lg p-6 md:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-3 mb-4">
              <RotateCcw className="w-6 h-6 text-indigo-400" />
              <h2 className="text-lg font-semibold">Configuration</h2>
            </div>
            <p className="text-gray-400 mb-4">Reload configurations and manage system settings.</p>
            <div className={`px-3 py-1 rounded text-sm font-medium mb-4 ${getStatusColor('healthy')}`}>
              Ready
            </div>
            <button 
              onClick={reloadConfiguration}
              className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
            >
              Reload Config
            </button>
          </div>
        </div>
      </div>

      {/* Modal */}
      {modalOpen && <AdminModal 
        data={modalData} 
        onClose={closeModal}
        onSave={saveConfig}
        onDownload={downloadLogs}
      />}

      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notification) => (
          <div
            key={notification.id}
            className={`max-w-sm p-4 rounded-lg shadow-lg transition-all duration-300 ${
              notification.type === 'error' ? 'bg-red-600 text-white' :
              notification.type === 'success' ? 'bg-green-600 text-white' :
              'bg-blue-600 text-white'
            }`}
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">{notification.message}</p>
              <button
                onClick={() => removeNotification(notification.id)}
                className="ml-2 text-white hover:text-gray-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Modal Component
const AdminModal = ({ data, onClose, onSave, onDownload }) => {
  const [content, setContent] = useState(data.content?.value || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    await onSave(content)
    setSaving(false)
  }

  const handleSaveAndClose = async () => {
    await handleSave()
    onClose()
  }

  const renderContent = () => {
    switch (data.content?.type) {
      case 'textarea':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                {data.title}
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full h-64 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg font-mono text-sm resize-vertical"
                placeholder="Enter configuration..."
              />
            </div>
            {data.content.description && (
              <p className="text-sm text-gray-400">{data.content.description}</p>
            )}
          </div>
        )

      case 'logs':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-medium">
                Recent Log Entries (last {data.content.lines} lines)
              </label>
              <button
                onClick={onDownload}
                className="flex items-center gap-2 px-3 py-1 bg-cyan-600 hover:bg-cyan-700 rounded text-sm transition-colors"
              >
                <Download className="w-4 h-4" />
                Download Full Log
              </button>
            </div>
            <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto whitespace-pre-wrap">
              {data.content.content}
            </div>
            <p className="text-sm text-gray-400">
              Showing {data.content.lines} of {data.content.totalLines} total lines.
            </p>
          </div>
        )

      case 'health':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-gray-700 rounded-lg">
              <p className="text-sm font-medium">
                Overall Status: <span className={`ml-2 px-2 py-1 rounded text-xs ${
                  data.content.overallStatus === 'healthy' ? 'bg-green-900 text-green-400' :
                  data.content.overallStatus === 'warning' ? 'bg-yellow-900 text-yellow-400' :
                  'bg-red-900 text-red-400'
                }`}>
                  {data.content.overallStatus}
                </span>
              </p>
            </div>
            <div className="space-y-3">
              {data.content.components?.map((component, index) => (
                <div key={index} className="p-3 border border-gray-600 rounded-lg">
                  <div className="flex items-center justify-between">
                    <strong>{component.component}</strong>
                    <span className={`px-2 py-1 rounded text-xs ${
                      component.status === 'healthy' ? 'bg-green-900 text-green-400' :
                      component.status === 'warning' ? 'bg-yellow-900 text-yellow-400' :
                      'bg-red-900 text-red-400'
                    }`}>
                      {component.status}
                    </span>
                  </div>
                  {component.details && (
                    <pre className="mt-2 text-xs text-gray-400 overflow-x-auto">
                      {JSON.stringify(component.details, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>
        )

      case 'mcp-health': {
        const summary = data.content.healthSummary
        return (
          <div className="space-y-4">
            <div className="p-4 bg-gray-700 rounded-lg space-y-2">
              <p><strong>Overall Status:</strong> <span className={`ml-2 px-2 py-1 rounded text-xs ${
                summary.overall_status === 'healthy' ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'
              }`}>{summary.overall_status}</span></p>
              <p><strong>Servers:</strong> {summary.healthy_count}/{summary.total_count} healthy</p>
              <p><strong>Last Check:</strong> {summary.last_check ? new Date(summary.last_check * 1000).toLocaleString() : 'Never'}</p>
              <p><strong>Check Interval:</strong> {summary.check_interval} seconds</p>
            </div>
            {summary.servers && (
              <div className="space-y-3">
                {Object.entries(summary.servers).map(([serverName, serverInfo]) => (
                  <div key={serverName} className="p-3 border border-gray-600 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <strong>{serverName}</strong>
                      <span className={`px-2 py-1 rounded text-xs ${
                        serverInfo.status === 'healthy' ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'
                      }`}>
                        {serverInfo.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400 space-y-1">
                      <p>Last Check: {new Date(serverInfo.last_check * 1000).toLocaleString()}</p>
                      {serverInfo.response_time_ms && <p>Response Time: {serverInfo.response_time_ms.toFixed(1)}ms</p>}
                      {serverInfo.error_message && <p>Error: {serverInfo.error_message}</p>}
                      <p>Running: {serverInfo.is_running ? 'Yes' : 'No'}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      }

      default:
        return <p>Unknown content type</p>
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto my-8">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">{data.title}</h2>
          
          {renderContent()}

          <div className="flex justify-end gap-3 mt-6">
            {!data.content?.readonly && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleSaveAndClose}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                  Done
                </button>
              </>
            )}
            {data.content?.readonly && (
              <button
                onClick={onClose}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
              >
                <Check className="w-4 h-4" />
                Done
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdminDashboard
