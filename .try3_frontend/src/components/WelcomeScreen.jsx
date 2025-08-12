
import React from 'react';
import { useConfig } from '../hooks/useApi'; // Assuming useApi.js exports useConfig

function WelcomeScreen() {
  const { config, error } = useConfig();

  if (error) {
    return <div className="text-red-500">Error loading configuration: {error.message}</div>;
  }

  if (!config) {
    return <div className="text-gray-400">Loading application configuration...</div>;
  }

  return (
    <div className="flex flex-col items-center justify-center h-full w-full">
      <img 
        src="/logo.png" // Path to the logo from the public directory
        alt="App Logo" 
        className="w-48 h-48 mb-4" // Adjust size as needed
      />
      <h1 className="text-4xl font-bold text-white">
        {config.app_name || "Chat Application"}
      </h1>
      
    </div>
  );
}

export default WelcomeScreen;
