
import { useState, useEffect } from 'react';

export function useConfig() {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/config')
      .then((res) => res.json())
      .then((data) => {
        console.log('Fetched config:', data);
        setConfig(data);
      })
      .catch((err) => setError(err));
  }, []);

  return { config, error };
}
