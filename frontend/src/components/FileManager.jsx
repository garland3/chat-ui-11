import { useState, useEffect } from 'react'
import { 
  File, 
  Image, 
  Database, 
  FileText, 
  Code, 
  Download, 
  Trash2, 
  ChevronDown, 
  ChevronRight,
  Upload,
  Zap
} from 'lucide-react'

const FileManager = ({ files, onDownloadFile, onDeleteFile }) => {
  const [expandedCategories, setExpandedCategories] = useState({
    code: true,
    image: true,
    data: true,
    document: true,
    other: true
  })

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'code':
        return <Code className="w-4 h-4 text-blue-400" />
      case 'image':
        return <Image className="w-4 h-4 text-green-400" />
      case 'data':
        return <Database className="w-4 h-4 text-yellow-400" />
      case 'document':
        return <FileText className="w-4 h-4 text-red-400" />
      default:
        return <File className="w-4 h-4 text-gray-400" />
    }
  }

  const getFileIcon = (file) => {
    switch (file.type) {
      case 'code':
        return <Code className="w-4 h-4 text-blue-400" />
      case 'image':
        return <Image className="w-4 h-4 text-green-400" />
      case 'data':
        return <Database className="w-4 h-4 text-yellow-400" />
      case 'document':
        return <FileText className="w-4 h-4 text-red-400" />
      default:
        return <File className="w-4 h-4 text-gray-400" />
    }
  }

  const getSourceBadge = (file) => {
    if (file.source === 'generated') {
      return (
        <div className="flex items-center gap-1">
          <Zap className="w-3 h-3 text-purple-400" />
          <span className="text-xs px-1.5 py-0.5 bg-purple-600/20 text-purple-300 rounded">
            {file.source_tool || 'Generated'}
          </span>
        </div>
      )
    } else {
      return (
        <div className="flex items-center gap-1">
          <Upload className="w-3 h-3 text-blue-400" />
          <span className="text-xs px-1.5 py-0.5 bg-blue-600/20 text-blue-300 rounded">
            Uploaded
          </span>
        </div>
      )
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }))
  }

  const getCategoryTitle = (category) => {
    switch (category) {
      case 'code':
        return 'Code Files'
      case 'image':
        return 'Images & Plots'
      case 'data':
        return 'Data Files'
      case 'document':
        return 'Documents'
      default:
        return 'Other Files'
    }
  }

  if (!files || files.total_files === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <File className="w-5 h-5 text-gray-400" />
          <h3 className="text-sm font-medium text-gray-200">Session Files</h3>
        </div>
        <div className="text-center py-6 text-gray-400">
          <File className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No files in this session</p>
          <p className="text-xs text-gray-500 mt-1">
            Upload files or use tools that generate files to see them here
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <File className="w-5 h-5 text-gray-400" />
          <h3 className="text-sm font-medium text-gray-200">Session Files</h3>
        </div>
        <span className="text-xs text-gray-400 px-2 py-1 bg-gray-700 rounded">
          {files.total_files} files
        </span>
      </div>

      <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
        {Object.entries(files.categories).map(([category, categoryFiles]) => {
          if (categoryFiles.length === 0) return null

          const isExpanded = expandedCategories[category]

          return (
            <div key={category} className="space-y-2">
              <button
                onClick={() => toggleCategory(category)}
                className="flex items-center gap-2 w-full text-left p-2 rounded hover:bg-gray-700/50 transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
                {getCategoryIcon(category)}
                <span className="text-sm font-medium text-gray-200">
                  {getCategoryTitle(category)}
                </span>
                <span className="text-xs text-gray-400 ml-auto">
                  {categoryFiles.length}
                </span>
              </button>

              {isExpanded && (
                <div className="ml-6 space-y-1">
                  {categoryFiles.map((file, index) => (
                    <div 
                      key={`${file.filename}-${index}`}
                      className="flex items-center gap-3 p-2 rounded hover:bg-gray-700/30 transition-colors group"
                    >
                      {getFileIcon(file)}
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start gap-2 mb-1">
                          <span className="text-sm text-gray-200 break-all font-mono">
                            {file.filename}
                          </span>
                          <div className="flex-shrink-0">{getSourceBadge(file)}</div>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <span>{formatFileSize(file.size)}</span>
                          <span>•</span>
                          <span className="uppercase">{file.extension}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => onDownloadFile?.(file.filename)}
                          className="p-1.5 text-gray-400 hover:text-blue-400 hover:bg-blue-400/10 rounded transition-colors"
                          title="Download file"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onDeleteFile?.(file.filename)}
                          className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded transition-colors"
                          title="Delete file"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default FileManager