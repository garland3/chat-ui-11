import React from 'react';
import LogViewer from './LogViewer';

export default function AdminPanel() {
  return (
    <div className="h-full flex flex-col">
      <header className="p-4 border-b border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <h1 className="text-xl font-bold">Admin Panel</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">System Logs</p>
      </header>
      <LogViewer />
    </div>
  );
}
