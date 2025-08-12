import { useState, useEffect } from 'react';

// Hook to fetch banner messages from backend /api/banners
export function useBanners() {
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    fetch('/api/banners')
      .then((res) => res.json())
      .then((data) => {
        if (!isMounted) return;
        if (data && Array.isArray(data.messages)) {
          setMessages(data.messages);
        } else {
          setMessages([]);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return { messages, error, loading };
}
