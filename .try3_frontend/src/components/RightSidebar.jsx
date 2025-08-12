import React, { useState, useEffect } from 'react';
import { useConfig } from '../hooks/useApi';

function RightSidebar({ isCollapsed, selectedModel, setSelectedModel, temperature, setTemperature }) {
  const { config, error } = useConfig();

  // Set default model when config loads
  useEffect(() => {
    if (config && config.models && config.models.length > 0 && !selectedModel) {
      setSelectedModel(config.models[0]);
    }
  }, [config, selectedModel, setSelectedModel]);

  if (error) {
    return <div>Error loading config: {error.message}</div>;
  }

  if (!config) {
    return <div>Loading...</div>;
  }

  if (isCollapsed) {
    return null;
  }

  return (
    <aside id="right-sidebar" className="w-80 bg-gray-100 flex-shrink-0 flex flex-col p-4 space-y-6 border-l border-gray-200 lg:relative dark:bg-gray-800 dark:border-gray-700">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Context</h2>
        <button className="lg:hidden">
          <i className="fas fa-times"></i>
        </button>
      </div>
      <div className="bg-gray-200 p-3 rounded-lg dark:bg-gray-700">
       
        <p className="text-sm">
          <strong>User:</strong> {config.user}
        </p>
       
        <button className="w-full mt-3 text-sm bg-red-600/50 hover:bg-red-600/80 text-white py-1 px-3 rounded-lg transition-all">
          Logout
        </button>
      </div>
      <div className="bg-gray-200 p-3 rounded-lg space-y-3 dark:bg-gray-700">
        <h3 className="font-semibold">Model Configuration</h3>
        <div>
          <label htmlFor="model-select" className="text-sm font-medium">
            Model
          </label>
          <select 
            id="model-select" 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full mt-1 bg-gray-300 border-gray-400 rounded-md p-2 text-sm focus:ring-cyan-500 focus:border-cyan-500 dark:bg-gray-600 dark:border-gray-500"
          >
            {config.models && config.models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="temp-slider" className="text-sm font-medium">
            Temperature: <span id="temp-value">{temperature}</span>
          </label>
          <input
            id="temp-slider"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
            className="w-full h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer dark:bg-gray-600"
          />
        </div>
      </div>
      {config.features?.tools && (
        <div className="bg-gray-200 p-3 rounded-lg space-y-3 dark:bg-gray-700">
          <h3 className="font-semibold">Tools</h3>
          <div id="tool-selection-list" className="space-y-2">
            {config.tools && config.tools.map((tool) => (
              <label key={tool.server} className="flex items-center space-x-2 text-sm">
                <input type="checkbox" className="form-checkbox bg-gray-300 border-gray-400 text-cyan-500 rounded focus:ring-cyan-500 dark:bg-gray-600 dark:border-gray-500" defaultChecked={true} />
                <span>{tool.server}</span>
              </label>
            ))}
          </div>
          {config.features?.marketplace && (
            <button className="w-full mt-2 text-sm bg-cyan-500/50 hover:bg-cyan-500/80 text-white py-1 px-3 rounded-lg transition-all">
              Browse Marketplace
            </button>
          )}
        </div>
      )}
      {config.features?.files_panel && (
        <div className="bg-gray-200 p-3 rounded-lg flex-grow flex flex-col dark:bg-gray-700">
          <h3 className="font-semibold mb-2">Uploaded Files</h3>
          <ul id="file-list" className="space-y-2 overflow-y-auto flex-grow"></ul>
        </div>
      )}
    </aside>
  );
}

export default RightSidebar;