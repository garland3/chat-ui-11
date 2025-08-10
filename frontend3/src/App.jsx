
import React, { useEffect, useState } from 'react';
import LeftSidebar from './components/LeftSidebar';
import MainContent from './components/MainContent';
import RightSidebar from './components/RightSidebar';
import Banner from './components/Banner';

function App() {
  // Load initial states from localStorage, default to false
  const [leftCollapsed, setLeftCollapsed] = useState(() => {
    const saved = localStorage.getItem('leftSidebarCollapsed');
    return saved !== null ? JSON.parse(saved) : false;
  });
  
  const [rightCollapsed, setRightCollapsed] = useState(() => {
    const saved = localStorage.getItem('rightSidebarCollapsed');
    return saved !== null ? JSON.parse(saved) : false;
  });

  // Theme management
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme || 'dark'; // Default to dark theme
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prevTheme) => (prevTheme === 'dark' ? 'light' : 'dark'));
  };

  // Save to localStorage whenever state changes
  useEffect(() => {
    localStorage.setItem('leftSidebarCollapsed', JSON.stringify(leftCollapsed));
  }, [leftCollapsed]);

  useEffect(() => {
    localStorage.setItem('rightSidebarCollapsed', JSON.stringify(rightCollapsed));
  }, [rightCollapsed]);

  useEffect(() => {
    console.log('App component mounted');
  }, []);

  return (
    <div className="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100 font-sans antialiased overflow-hidden h-screen flex flex-col">
      <Banner />
      <div id="app" className="flex flex-1 w-screen relative">
        <LeftSidebar 
          isCollapsed={leftCollapsed} 
          onToggleCollapse={() => setLeftCollapsed(!leftCollapsed)} 
        />
        <MainContent 
          leftCollapsed={leftCollapsed}
          rightCollapsed={rightCollapsed}
          onToggleLeft={() => setLeftCollapsed(!leftCollapsed)}
          onToggleRight={() => setRightCollapsed(!rightCollapsed)}
          theme={theme} // Pass theme to MainContent
          toggleTheme={toggleTheme} // Pass toggleTheme to MainContent
        />
        <RightSidebar 
          isCollapsed={rightCollapsed} 
        />
      </div>
    </div>
  );
}

export default App;
