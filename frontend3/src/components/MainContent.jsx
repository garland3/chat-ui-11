
import React, { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import WelcomeScreen from './WelcomeScreen';

function MainContent({ leftCollapsed, rightCollapsed, onToggleLeft, onToggleRight, theme, toggleTheme }) {
  const wsUrl = `ws://${window.location.host}/ws`;
  const { messages, sendMessage, error } = useWebSocket(wsUrl);
  const [prompt, setPrompt] = useState('');

  const handleSendMessage = () => {
    if (prompt.trim()) {
      sendMessage(prompt);
      setPrompt('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <main id="main-content" className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900 relative">
      {/* Sidebar Collapse Toggles (Desktop) */}
      <button 
        className="hidden lg:flex absolute top-1/2 -left-3 z-20 w-6 h-16 bg-gray-200 hover:bg-cyan-600 rounded-r-lg items-center justify-center transition-all dark:bg-gray-700 dark:hover:bg-cyan-600"
        onClick={onToggleLeft}
        title={leftCollapsed ? "Expand left sidebar" : "Collapse left sidebar"}
      >
        <i id="left-toggle-icon" className={`fas ${leftCollapsed ? 'fa-chevron-right' : 'fa-chevron-left'}`}></i>
      </button>
      <button 
        className="hidden lg:flex absolute top-1/2 -right-3 z-20 w-6 h-16 bg-gray-200 hover:bg-cyan-600 rounded-l-lg items-center justify-center transition-all dark:bg-gray-700 dark:hover:bg-cyan-600"
        onClick={onToggleRight}
        title={rightCollapsed ? "Expand right sidebar" : "Collapse right sidebar"}
      >
        <i id="right-toggle-icon" className={`fas ${rightCollapsed ? 'fa-chevron-left' : 'fa-chevron-right'}`}></i>
      </button>

      {/* Main Header */}
      <header className="flex-shrink-0 flex justify-between items-center px-4 border-b border-gray-200 bg-gray-100/50 backdrop-blur-sm h-14 dark:border-gray-700 dark:bg-gray-800/50">
        <div className="flex items-center space-x-4">
          <button className="lg:hidden">
            <i className="fas fa-bars"></i>
          </button>
          
        </div>
        <div className="flex items-center space-x-4">
          <div id="websocket-status" className="flex items-center space-x-2 text-sm">
            <div id="ws-indicator" className="w-3 h-3 rounded-full bg-green-500"></div>
            <span id="ws-text" className="text-gray-600 dark:text-gray-400">Connected</span>
          </div>
          <button 
            onClick={toggleTheme} 
            className="p-2 rounded-full hover:bg-gray-700 transition-colors"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            <i className={`fas ${theme === 'dark' ? 'fa-sun text-yellow-400' : 'fa-moon text-gray-400'}`}></i>
          </button>
          <button className="lg:hidden">
            <i className="fas fa-cog"></i>
          </button>
        </div>
      </header>

      {/* Side-by-Side Content Panels */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Chat Panel */}
        <div id="chat-panel" className="w-full flex flex-col overflow-hidden transition-all">
          {/* Mobile Tabs Header */}
          <div className="lg:hidden flex-shrink-0 flex space-x-4 px-4 border-b border-gray-200 dark:border-gray-700">
            <button id="tab-chat" className="tab-button py-3 px-2 text-sm font-semibold text-gray-600 dark:text-gray-400">
              Chat
            </button>
            <button id="tab-canvas" className="tab-button py-3 px-2 text-sm font-semibold text-gray-600 dark:text-gray-400">
              Canvas
            </button>
          </div>
          <div id="chat-container-wrapper" className="flex-1 flex flex-col overflow-hidden">
            <div id="chat-container" className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.length === 0 ? (
                <WelcomeScreen />
              ) : (
                messages.map((msg, index) => (
                  <div key={index} className="flex items-start gap-3">
                    
                    <div className="bg-gray-200 p-3 rounded-lg max-w-2xl w-full dark:bg-gray-800">
                      <div className="prose prose-invert text-gray-900 dark:text-gray-300">
                        {msg}
                      </div>
                      <div className="mt-2 pt-2 border-t border-gray-300 flex items-center justify-between dark:border-gray-700">
                        <span className="text-xs text-gray-600 dark:text-gray-500">Assistant</span>
                        <div className="flex items-center space-x-3 text-gray-600 dark:text-gray-500">
                          <button className="hover:text-white">
                            <i className="fas fa-thumbs-up"></i>
                          </button>
                          <button className="hover:text-white">
                            <i className="fas fa-thumbs-down"></i>
                          </button>
                          <button className="hover:text-white">
                            <i className="fas fa-copy"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            {/* -------------------- 
            Main text input area for chat. 
            -----------------------------
            */}
            <div className="p-4 bg-gray-100 border-t border-gray-200 dark:bg-gray-800 dark:border-gray-700">
              <div className="relative bg-gray-200 rounded-lg dark:bg-gray-700">
                <textarea
                  id="prompt-input"
                  rows="1"
                  className="w-full bg-transparent p-4 pr-24 rounded-lg resize-none focus:outline-none"
                  placeholder="Ask to me anything..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                ></textarea>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center space-x-3">
                  <label htmlFor="file-upload-input" className="cursor-pointer text-gray-600 hover:text-white dark:text-gray-400">
                    <i className="fas fa-paperclip"></i>
                  </label>
                  <input type="file" id="file-upload-input" multiple className="hidden" />
                  <button
                    className="bg-cyan-500 hover:bg-cyan-600 text-white rounded-full w-8 h-8 flex items-center justify-center"
                    onClick={handleSendMessage}
                  >
                    <i className="fas fa-arrow-up"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Canvas Panel */}
        <div id="canvas-panel" className="hidden lg:flex w-full lg:w-0 flex-col overflow-hidden border-l border-gray-200 dark:border-gray-700 transition-all">
          <div className="flex-shrink-0 flex justify-between items-center px-4 h-14 border-b border-gray-200 bg-gray-100/50 dark:border-gray-700 dark:bg-gray-800/50">
            <h3 className="text-lg font-semibold">Canvas</h3>
            <button className="text-gray-600 hover:text-white dark:text-gray-400">
              <i className="fas fa-times"></i>
            </button>
          </div>
          <div id="canvas-content" className="flex-1 p-6 overflow-y-auto">
            {/* Visual outputs appear here */}
          </div>
        </div>
      </div>
    </main>
  );
}

export default MainContent;
