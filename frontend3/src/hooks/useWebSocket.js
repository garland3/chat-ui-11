
import { useState, useEffect } from 'react';

export function useWebSocket(url) {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setSocket(ws);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'chat_response') {
          setMessages((prevMessages) => [...prevMessages, { role: 'assistant', content: data.message }]);
        }
      } catch (error) {
        // Fallback for non-JSON messages
        setMessages((prevMessages) => [...prevMessages, { role: 'assistant', content: event.data }]);
      }
    };

    ws.onerror = (err) => {
      setError(err);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setSocket(null);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const sendMessage = (message, model, temperature) => {
    if (socket) {
      // Add user message to UI immediately
      setMessages((prevMessages) => [...prevMessages, { role: 'user', content: message }]);
      
      const messageData = {
        type: "chat",
        content: message,
        model: model,
        temperature: temperature
      };
      socket.send(JSON.stringify(messageData));
    }
  };

  return { messages, sendMessage, error };
}
