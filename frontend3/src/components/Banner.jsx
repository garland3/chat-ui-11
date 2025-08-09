import React, { useState, useEffect } from 'react';
import { useConfig } from '../hooks/useApi';

function Banner() {
  const [isVisible, setIsVisible] = useState(true);
  const { config } = useConfig();

  // Hide entirely if feature is disabled or config not yet loaded
  if (!config || !config.banner_enabled) return null;
  if (!isVisible) return null;

  return (
    <div className="bg-cyan-600 text-white text-center p-2 text-sm flex justify-between items-center">
      <span className="flex items-center gap-2">
        <img src="/agent11.png" alt="logo" className="w-5 h-5 opacity-90" />
        <span>
          Welcome to {config.app_name}! ✨{' '}
          <a href="#" className="underline font-semibold">
            Learn more
          </a>
        </span>
      </span>
      <button onClick={() => setIsVisible(false)} className="px-2" aria-label="Close banner">
        &times;
      </button>
    </div>
  );
}

export default Banner;