import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import WelcomeScreen from './WelcomeScreen';
import MarkdownRenderer from './MarkdownRenderer';

function MainContent({ leftCollapsed, rightCollapsed, onToggleLeft, onToggleRight, theme, toggleTheme, selectedModel, temperature }) {
  const wsUrl = `ws://${window.location.host}/ws`;
  const { messages, sendMessage, error, setMessages, isThinking } = useWebSocket(wsUrl);
  const [prompt, setPrompt] = useState('');
  const [editingIndex, setEditingIndex] = useState(null);
  const [editText, setEditText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);

  const promptInputRef = useRef(null);
  const chatContainerRef = useRef(null);
  const bottomSentinelRef = useRef(null); // sentinel element at bottom for smooth scrolling
  const autoScrollRef = useRef(true); // whether we should auto-scroll on new content
  const isScrollingRef = useRef(false); // track if currently programmatically scrolling
  const fileInputRef = useRef(null);

  // Scroll event tracking to update whether user is near bottom
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;
    const handleScroll = () => {
      // Don't update scroll state if we're programmatically scrolling
      if (isScrollingRef.current) return;
      
      const threshold = 140; // px distance from bottom considered "near"
      const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
      autoScrollRef.current = distanceFromBottom < threshold;
    };
    container.addEventListener('scroll', handleScroll, { passive: true });
    // Initialize
    handleScroll();
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    if (promptInputRef.current) {
      promptInputRef.current.focus();
    }
  }, []);

  // Scroll to bottom sentinel (instead of manual math) if allowed
  const scrollToBottom = useCallback((behavior = 'smooth') => {
    isScrollingRef.current = true;
    if (bottomSentinelRef.current) {
      bottomSentinelRef.current.scrollIntoView({ behavior, block: 'end' });
    } else if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({ top: chatContainerRef.current.scrollHeight, behavior });
    }
    // Reset flag after scroll completes
    setTimeout(() => {
      isScrollingRef.current = false;
    }, behavior === 'smooth' ? 500 : 100);
  }, []);

  // Decide when to auto-scroll: only on new messages if user was near bottom, or if thinking
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    const shouldScroll = (autoScrollRef.current && messages.length > 0) || (lastMessage && lastMessage.role === 'user') || isThinking;
    if (shouldScroll) {
      // Use rAF + small timeout to ensure DOM (esp. Markdown rendering) has laid out
      requestAnimationFrame(() => setTimeout(() => scrollToBottom('smooth'), 40));
    }
  }, [messages, isThinking, scrollToBottom]);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);
  };

  const handleSendMessage = async () => {
    if (prompt.trim() || selectedFiles.length > 0) {
      // If files are selected, we need to read them and send them with the message
      if (selectedFiles.length > 0) {
        const filesData = {};
        
        // Read all files as base64
        for (const file of selectedFiles) {
          const reader = new FileReader();
          const fileData = await new Promise((resolve) => {
            reader.onload = (e) => {
              // Remove the data URL prefix (e.g., "data:image/png;base64,")
              const base64 = e.target.result.split(',')[1];
              resolve(base64);
            };
            reader.readAsDataURL(file);
          });
          
          filesData[file.name] = fileData;
        }
        
        // Send message with files
        sendMessage(prompt, selectedModel, temperature, filesData);
        
        // Clear selected files
        setSelectedFiles([]);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        // Send message without files
        sendMessage(prompt, selectedModel, temperature);
      }
      
      setPrompt('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCopyMessage = (content) => {
    navigator.clipboard.writeText(content);
  };

  const handleEditMessage = (index) => {
    setEditingIndex(index);
    setEditText(messages[index].content);
  };

  const handleSaveEdit = () => {
    if (editText.trim()) {
      // Update the message at editingIndex
      const updatedMessages = [...messages];
      updatedMessages[editingIndex] = { ...updatedMessages[editingIndex], content: editText };
      
      // Truncate messages from this point forward (remove all messages after the edited one)
      const truncatedMessages = updatedMessages.slice(0, editingIndex + 1);
      setMessages(truncatedMessages);
      
      // Send the edited message
      sendMessage(editText, selectedModel, temperature);
      
      // Reset edit state
      setEditingIndex(null);
      setEditText('');
    }
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditText('');
  };

  return (
    <main id="main-content" className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-800 relative h-screen">
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
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
        {/* Chat Panel */}
        <div id="chat-panel" className="w-full flex flex-col overflow-hidden transition-all min-h-0">
          {/* Mobile Tabs Header */}
          <div className="lg:hidden flex-shrink-0 flex space-x-4 px-4 border-b border-gray-200 dark:border-gray-700">
            <button id="tab-chat" className="tab-button py-3 px-2 text-sm font-semibold text-gray-600 dark:text-gray-400">
              Chat
            </button>
            <button id="tab-canvas" className="tab-button py-3 px-2 text-sm font-semibold text-gray-600 dark:text-gray-400">
              Canvas
            </button>
          </div>
          <div id="chat-container-wrapper" className="flex-1 flex flex-col overflow-hidden min-h-0">
            <div id="chat-container" ref={chatContainerRef} className="flex-1 overflow-y-auto p-6 space-y-6 min-h-0 no-scrollbar">
              {messages.length === 0 ? (
                <WelcomeScreen />
              ) : (
                messages.map((msg, index) => (
                  <div key={index} className={`flex mb-8 ${msg.role === 'user' ? 'justify-end' : 'justify-center'}`}>
                    <div className={`px-6 py-4 rounded-lg relative group break-words overflow-hidden ${
                      msg.role === 'user'
                        ? 'bg-gray-200 text-gray-900 dark:bg-gray-800 dark:text-gray-300 mr-12 max-w-4xl'
                        : 'text-gray-900 dark:text-gray-300 w-full max-w-[110ch] mx-auto'
                    }`}>
                      {editingIndex === index ? (
                        <div className="space-y-3">
                          <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            className="w-full p-2 rounded bg-white text-gray-900 resize-none"
                            rows="3"
                            autoFocus
                          />
                          <div className="flex justify-end space-x-2">
                            <button
                              onClick={handleCancelEdit}
                              className="px-3 py-1 text-sm bg-gray-500 hover:bg-gray-600 rounded"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleSaveEdit}
                              className="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 rounded"
                            >
                              Save & Send
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="whitespace-pre-wrap">
                            {msg.role === 'assistant' ? (
                              <MarkdownRenderer content={msg.content} />
                            ) : (
                              msg.content
                            )}
                          </div>
                          {msg.role === 'user' && (
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <div className="flex items-center space-x-2 bg-gray-300 dark:bg-gray-700 rounded-lg px-2 py-1">
                                <button 
                                  onClick={() => handleCopyMessage(msg.content)}
                                  className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm"
                                  title="Copy message"
                                >
                                  <i className="fas fa-copy"></i>
                                </button>
                                <button 
                                  onClick={() => handleEditMessage(index)}
                                  className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm"
                                  title="Edit message"
                                >
                                  <i className="fas fa-edit"></i>
                                </button>
                              </div>
                            </div>
                          )}
                          {msg.role === 'assistant' && (
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <div className="flex items-center space-x-2 bg-gray-300 dark:bg-gray-700 rounded-lg px-2 py-1">
                                <button 
                                  className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm"
                                  title="Thumbs up"
                                >
                                  <i className="fas fa-thumbs-up"></i>
                                </button>
                                <button 
                                  className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm"
                                  title="Thumbs down"
                                >
                                  <i className="fas fa-thumbs-down"></i>
                                </button>
                                <button 
                                  onClick={() => handleCopyMessage(msg.content)}
                                  className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm"
                                  title="Copy message"
                                >
                                  <i className="fas fa-copy"></i>
                                </button>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}
              {isThinking && (
                <div className="flex justify-start mb-6">
                  <div className="max-w-4xl w-full px-4 py-3 rounded-lg bg-gray-200 text-gray-900 dark:bg-gray-800 dark:text-gray-300 ml-12">
                    <div className="flex items-center space-x-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                      </div>
                      <span className="text-gray-500 text-sm">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              {/* Bottom sentinel for scroll anchoring */}
              <div ref={bottomSentinelRef} />
            </div>
            {/* -------------------- 
            Main text input area for chat. 
            -----------------------------
            */}
            <div className="flex-shrink-0 p-4 bg-gray-100 border-t border-gray-200 dark:bg-gray-800 dark:border-gray-700">
              <div className="relative bg-gray-200 rounded-lg dark:bg-gray-700">
                {selectedFiles.length > 0 && (
                  <div className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 border-b border-gray-300 dark:border-gray-600">
                    Selected files: {selectedFiles.map(file => file.name).join(', ')}
                  </div>
                )}
                <textarea
                  id="prompt-input"
                  rows="1"
                  className="w-full bg-transparent p-4 pr-24 rounded-lg resize-none focus:outline-none"
                  placeholder="Ask to me anything..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  ref={promptInputRef}
                ></textarea>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center space-x-3">
                  <label htmlFor="file-upload-input" className="cursor-pointer text-gray-600 hover:text-white dark:text-gray-400">
                    <i className="fas fa-paperclip"></i>
                  </label>
                  <input 
                    type="file" 
                    id="file-upload-input" 
                    multiple 
                    className="hidden" 
                    ref={fileInputRef}
                    onChange={handleFileChange}
                  />
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
