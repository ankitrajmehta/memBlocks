import React, { useState } from 'react';
import ChatPanel from './components/ChatPanel';
import OptionsPanel from './components/OptionsPanel';

/**
 * Main App Component
 * Implements split-screen layout: Chat on left, Options on right
 */
function App() {
  // Global state
  const [currentUser, setCurrentUser] = useState(null);
  const [currentBlock, setCurrentBlock] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const handleUserSelect = (user) => {
    setCurrentUser(user);
    setCurrentBlock(null); // Reset block when user changes
    setSessionId(null); // Reset session
  };

  const handleBlockSelect = (block) => {
    setCurrentBlock(block);
    setSessionId(null); // Reset session when block changes
  };

  const handleSessionStart = (newSessionId) => {
    setSessionId(newSessionId);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-primary-600 to-primary-800 text-white shadow-lg">
        <div className="px-6 py-4">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <span className="text-4xl">🧠</span>
            <span>memBlocks</span>
          </h1>
          <p className="text-primary-100 text-sm mt-1">
            Intelligent Memory Management for LLMs
          </p>
        </div>
      </header>

      {/* Main Content - Split View */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 overflow-hidden min-h-0">
        {/* Left Half - Chat Panel */}
        <div className="min-h-0">
          <ChatPanel
            sessionId={sessionId}
            currentUser={currentUser}
            currentBlock={currentBlock}
          />
        </div>

        {/* Right Half - Options Panel */}
        <div className="min-h-0">
          <OptionsPanel
            currentUser={currentUser}
            currentBlock={currentBlock}
            sessionId={sessionId}
            onUserSelect={handleUserSelect}
            onBlockSelect={handleBlockSelect}
            onSessionStart={handleSessionStart}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-gray-300 text-center py-3 text-sm">
        <p>
          memBlocks © 2024 | Backend: 
          <code className="bg-gray-700 px-2 py-1 rounded ml-2 text-green-400">
            http://localhost:8001
          </code>
        </p>
      </footer>
    </div>
  );
}

export default App;
