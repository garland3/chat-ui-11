
import { useState, useEffect } from 'react';

export function useWebSocket(url) {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [isThinking, setIsThinking] = useState(false);

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
          setIsThinking(false);
          setMessages((prevMessages) => [...prevMessages, { role: 'assistant', content: data.message }]);
        }
      } catch (error) {
        // Fallback for non-JSON messages
        setIsThinking(false);
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

  const sendMessage = (message, model, temperature, files = null) => {
    if (socket) {
      // Add user message to UI immediately
      let content = message;
      if (files && Object.keys(files).length > 0) {
        const fileNames = Object.keys(files).join(', ');
        content = message ? `${message}\n\nAttached files: ${fileNames}` : `Attached files: ${fileNames}`;
      }
      
      setMessages((prevMessages) => [...prevMessages, { role: 'user', content }]);
      
      // Set thinking state
      setIsThinking(true);
      
      const messageData = {
        type: "chat",
        content: message,
        model: model,
        temperature: temperature
      };
      
      // Add files to message data if present
      if (files && Object.keys(files).length > 0) {
        messageData.files = files;
      }
      
      socket.send(JSON.stringify(messageData));
    }
  };

  return { messages, sendMessage, error, setMessages, isThinking };
}
