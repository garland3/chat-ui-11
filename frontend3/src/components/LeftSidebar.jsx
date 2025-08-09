import React from 'react';
import { useConfig } from '../hooks/useApi';

function LeftSidebar() {
  const { config, error } = useConfig();

  if (error) {
    return <div>Error loading config: {error.message}</div>;
  }

  if (!config) {
    return <div>Loading...</div>;
  }

  const features = config.features || {};

  return (
    <aside id="left-sidebar" className="w-72 bg-gray-800 flex-shrink-0 flex flex-col p-4 space-y-4 border-r border-gray-700 lg:relative">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-bold">{config.app_name}</h1>
        <button className="lg:hidden">
          <i className="fas fa-times"></i>
        </button>
      </div>
      {features.workspaces && (
        <div>
          <label htmlFor="workspace-select" className="text-sm font-semibold text-gray-400 mb-1 block">
            Workspace
          </label>
          <select id="workspace-select" className="w-full bg-gray-700 border-gray-600 rounded-md p-2 text-sm focus:ring-cyan-500 focus:border-cyan-500">
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
        {features.chat_history && (
          <div>
            <h2 className="text-sm font-semibold text-gray-400 mb-2">History</h2>
            <ul id="conversation-list" className="space-y-2">
              {/* Placeholder history items when feature enabled */}
              <li className="bg-gray-700 p-2 rounded-lg cursor-pointer hover:bg-gray-600 transition-all">
                Analyze sales_data.csv
              </li>
              <li className="p-2 rounded-lg cursor-pointer hover:bg-gray-600 transition-all">
                Draft marketing copy
              </li>
            </ul>
          </div>
        )}
        {features.rag && (
          <div>
              <h2 className="text-sm font-semibold text-gray-400 mb-2">RAG Sources</h2>
            <input
              type="search"
              id="rag-search"
              placeholder="Filter sources..."
              className="w-full bg-gray-700 border-gray-600 rounded-md p-2 text-sm mb-2 focus:ring-cyan-500 focus:border-cyan-500"
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