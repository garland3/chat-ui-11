import React, { useState, useEffect } from 'react';
import { useConfig } from '../hooks/useApi';
import { useBanners } from '../hooks/useBanners';

function Banner() {
  const [isVisible, setIsVisible] = useState(true);
  const [activeIndex, setActiveIndex] = useState(0);
  const { config } = useConfig();
  const { messages, loading } = useBanners();

  const hasMessages = messages && messages.length > 0;

  // Rotate messages every 8s if multiple (hook must always run to keep order stable)
  useEffect(() => {
    if (!hasMessages || messages.length < 2) return;
    const id = setInterval(() => {
      setActiveIndex((i) => (i + 1) % messages.length);
    }, 8000);
    return () => clearInterval(id);
  }, [hasMessages, messages]);

  // Not ready or disabled or closed
  if (!config || !config.banner_enabled || !isVisible) {
    return null;
  }

  const currentMessage = hasMessages ? messages[activeIndex] : `Welcome to ${config.app_name}!`;

  return (
    <div className="bg-cyan-600 text-white text-center p-2 text-sm flex justify-between items-center">
      <span className="flex items-center gap-2">
        <img src="/agent11.png" alt="logo" className="w-5 h-5 opacity-90" />
        <span>{currentMessage}</span>
      </span>
      <div className="flex items-center gap-2">
        {hasMessages && messages.length > 1 && (
          <span className="text-xs opacity-70">{activeIndex + 1}/{messages.length}</span>
        )}
        <button onClick={() => setIsVisible(false)} className="px-2" aria-label="Close banner">
          &times;
        </button>
      </div>
    </div>
  );
}

export default Banner;