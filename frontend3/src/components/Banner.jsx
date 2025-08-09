import React, { useState } from 'react';

function Banner() {
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  return (
    <div className="bg-cyan-600 text-white text-center p-2 text-sm flex justify-between items-center">
      <span>
        Welcome to the new Gemini interface! ✨{' '}
        <a href="#" className="underline font-semibold">
          Learn more
        </a>
      </span>
      <button onClick={() => setIsVisible(false)} className="px-2">
        &times;
      </button>
    </div>
  );
}

export default Banner;