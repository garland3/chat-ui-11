import { useState, useEffect } from 'react'
import { 
  File, 
  Image, 
  Database, 
  FileText, 
  Code, 
  Download, 
  Trash2
} from 'lucide-react'

const FileManager = ({ files, onDownloadFile, onDeleteFile }) => {


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


  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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

      <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
        {files.files.map((file, index) => (
          <div 
            key={`${file.filename}-${index}`}
            className="flex items-center gap-3 p-3 rounded hover:bg-gray-700/30 transition-colors group border border-gray-600/50"
          >
            {getFileIcon(file)}
            
            <div className="flex-1 min-w-0">
              <div className="mb-1">
                <span className="text-sm text-gray-200 break-all font-mono">
                  {file.filename}
                </span>
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
    </div>
  )
}

export default FileManager