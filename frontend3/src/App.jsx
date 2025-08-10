
import React, { useEffect } from 'react';
import LeftSidebar from './components/LeftSidebar';
import MainContent from './components/MainContent';
import RightSidebar from './components/RightSidebar';
import Banner from './components/Banner';

function App() {
  useEffect(() => {
    console.log('App component mounted');
  }, []);

  return (
    <div className="bg-gray-900 text-gray-100 font-sans antialiased overflow-hidden h-screen flex flex-col">
      <Banner />
      <div id="app" className="flex flex-1 w-screen relative">
        <LeftSidebar />
        <MainContent />
        <RightSidebar />
      </div>
    </div>
  );
}

export default App;
