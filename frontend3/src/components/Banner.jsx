import React, { useState, useEffect } from 'react';

function Banner() {
  const [messages, setMessages] = useState([]);
  const [dismissedMessages, setDismissedMessages] = useState(new Set());

  useEffect(() => {
    const fetchBannerMessages = async () => {
      try {
        const response = await fetch('/api/banners');
        if (response.ok) {
          const data = await response.json();
          if (data.messages && data.messages.length > 0) {
            setMessages(data.messages);
          }
        }
      } catch (error) {
        console.error('Error fetching banner messages:', error);
      }
    };

    fetchBannerMessages();
  }, []);

  const handleDismiss = (messageIndex) => {
    setDismissedMessages(prev => new Set([...prev, messageIndex]));
  };

  const visibleMessages = messages.filter((_, index) => !dismissedMessages.has(index));

  if (visibleMessages.length === 0) return null;

  return (
    <div className="w-full">
      {visibleMessages.map((message, index) => {
        const originalIndex = messages.indexOf(message);
        return (
          <div key={originalIndex} className="w-full bg-cyan-600 text-white text-center p-2 text-sm flex justify-between items-center border-b border-cyan-700 last:border-b-0">
            <span>
              {message}
            </span>
            <button 
              onClick={() => handleDismiss(originalIndex)} 
              className="px-2 hover:bg-cyan-700 rounded"
            >
              &times;
            </button>
          </div>
        );
      })}
    </div>
  );
}

export default Banner;