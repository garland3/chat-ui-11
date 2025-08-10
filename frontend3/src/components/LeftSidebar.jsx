import React from 'react';
import { Link } from 'react-router-dom';
import { useConfig } from '../hooks/useApi';

function LeftSidebar({ isCollapsed, onToggleCollapse }) {
  const { config, error } = useConfig();

  if (error) {
    return <div>Error loading config: {error.message}</div>;
  }

  if (!config) {
    return <div>Loading...</div>;
  }

  if (isCollapsed) {
    return (
      <aside id="left-sidebar" className="w-16 bg-gray-100 flex-shrink-0 flex flex-col p-2 space-y-4 border-r border-gray-200 lg:relative dark:bg-gray-800 dark:border-gray-700">
        <div className="flex flex-col items-center space-y-4">
          <button 
            onClick={onToggleCollapse}
            className="p-2 hover:bg-gray-200 rounded-lg transition-all dark:hover:bg-gray-700"
            title="Expand sidebar"
          >
            <i className="fas fa-bars text-gray-600 dark:text-gray-400"></i>
          </button>
          <button 
            className="p-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-all"
            title="New Chat"
          >
            <i className="fas fa-plus"></i>
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside id="left-sidebar" className="w-72 bg-gray-100 flex-shrink-0 flex flex-col p-4 space-y-4 border-r border-gray-200 lg:relative dark:bg-gray-800 dark:border-gray-700">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold">{config.app_name || 'Chat UI'}</h1>
        <button className="lg:hidden">
          <i className="fas fa-times"></i>
        </button>
      </div>
      {config.is_in_admin_group && (
        <Link to="/admin" className="w-full bg-gray-300 hover:bg-gray-400 text-gray-800 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600 font-semibold py-2 px-4 rounded-lg transition-all flex items-center justify-center text-sm">
          <i className="fas fa-shield-alt mr-2"></i> Admin Panel
        </Link>
      )}
      {config.features?.workspaces && (
        <div>
          <label htmlFor="workspace-select" className="text-sm font-semibold text-gray-600 mb-1 block dark:text-gray-400">
            Workspace
          </label>
          <select id="workspace-select" className="w-full bg-gray-200 border-gray-300 rounded-md p-2 text-sm focus:ring-cyan-500 focus:border-cyan-500 dark:bg-gray-700 dark:border-gray-600">
            {config.workspaces && config.workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </option>
            ))}
          </select>
        </div>
      )}
      <button className="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-2 px-4 rounded-lg transition-all flex items-center justify-center">
        <i className="fas fa-plus mr-2"></i> New Chat
      </button>
      <div className="flex-grow overflow-y-auto space-y-4">
        {config.features?.chat_history && (
          <div>
            <h2 className="text-sm font-semibold text-gray-600 mb-2 dark:text-gray-400">History</h2>
            <ul id="conversation-list" className="space-y-2">
              <li className="bg-gray-200 p-2 rounded-lg cursor-pointer hover:bg-gray-300 transition-all dark:bg-gray-700 dark:hover:bg-gray-600">
                Analyze sales_data.csv
              </li>
              <li className="p-2 rounded-lg cursor-pointer hover:bg-gray-600 transition-all">
                Draft marketing copy
              </li>
            </ul>
          </div>
        )}
        {config.features?.rag && (
          <div>
            <h2 className="text-sm font-semibold text-gray-600 mb-2 dark:text-gray-400">RAG Sources</h2>
            <input
              type="search"
              id="rag-search"
              placeholder="Filter sources..."
              className="w-full bg-gray-200 border-gray-300 rounded-md p-2 text-sm mb-2 focus:ring-cyan-500 focus:border-cyan-500 dark:bg-gray-700 dark:border-gray-600"
            />
            <div id="rag-source-list" className="space-y-2"></div>
            <button id="rag-show-more" className="text-cyan-400 text-sm mt-2 hover:underline">
              Show More
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

export default LeftSidebar;