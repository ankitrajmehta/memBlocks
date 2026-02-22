import React, { useState, Fragment } from 'react';
import UserSelector from './UserSelector';
import BlockSelector from './BlockSelector';
import MemoryViewer from './MemoryViewer';
import SummaryViewer from './SummaryViewer';
import ProcessingHistoryViewer from './ProcessingHistoryViewer';
import * as api from '../api/client';

/**
 * OptionsPanel Component
 * Contains all controls for managing users, blocks, and sessions
 */
const OptionsPanel = ({ 
  currentUser, 
  currentBlock, 
  sessionId,
  onUserSelect, 
  onBlockSelect, 
  onSessionStart 
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  
  // Modal states
  const [showMemoryViewer, setShowMemoryViewer] = useState(false);
  const [showSummaryViewer, setShowSummaryViewer] = useState(false);
  const [showProcessingHistory, setShowProcessingHistory] = useState(false);

  const handleStartSession = async () => {
    if (!currentUser || !currentBlock) {
      setError('Please select both a user and a block first');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);
      
      const session = await api.startSession(currentUser.user_id, currentBlock.meta_data.id);
      onSessionStart(session.session_id);
      setSuccessMessage('✅ Chat session started successfully!');
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.message);
      console.error('Failed to start session:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewMemory = () => {
    if (!currentBlock) {
      setError('Please select a block first');
      return;
    }
    setShowMemoryViewer(true);
  };

  const handleViewSummary = () => {
    if (!currentBlock) {
      setError('Please select a block first');
      return;
    }
    setShowSummaryViewer(true);
  };

  const handleViewProcessingHistory = () => {
    if (!sessionId) {
      setError('No active session');
      return;
    }
    setShowProcessingHistory(true);
  };

  return (
    <>
    <div className="h-full flex flex-col bg-gray-50 rounded-lg shadow-md overflow-hidden">
      <div className="flex-none p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-gray-800">⚙️ Control Panel</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-6 min-h-0">
        {/* User Selection */}
        <UserSelector 
          currentUser={currentUser} 
          onUserSelect={onUserSelect} 
        />

        {/* Block Selection */}
        <BlockSelector 
          currentUser={currentUser}
          currentBlock={currentBlock}
          onBlockSelect={onBlockSelect}
        />

      {/* Actions Section */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-4">
        <h2 className="text-xl font-bold mb-4 text-gray-800">🎬 Actions</h2>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Success Display */}
        {successMessage && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
            {successMessage}
          </div>
        )}

        {/* Start Session Button */}
        <button
          onClick={handleStartSession}
          disabled={!currentUser || !currentBlock || loading}
          className="w-full px-4 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all font-medium mb-3 shadow-md"
        >
          {loading ? (
            <div className="flex items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              <span>Starting Session...</span>
            </div>
          ) : (
            '🚀 Start Chat Session'
          )}
        </button>

        {/* View Memory Button */}
        <button
          onClick={handleViewMemory}
          disabled={!currentBlock}
          className="w-full px-4 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg hover:from-primary-600 hover:to-primary-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all font-medium mb-3 shadow-md"
        >
          🧠 View Core Memory
        </button>

        {/* View Summary Button */}
        <button
          onClick={handleViewSummary}
          disabled={!currentBlock}
          className="w-full px-4 py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg hover:from-purple-600 hover:to-purple-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all font-medium mb-3 shadow-md"
        >
          📚 View Recursive Summary
        </button>

        {/* View Processing History Button */}
        <button
          onClick={handleViewProcessingHistory}
          disabled={!sessionId}
          className="w-full px-4 py-3 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-lg hover:from-orange-600 hover:to-orange-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all font-medium shadow-md"
        >
          ⚙️ View Processing History
        </button>
      </div>

      {/* Status Section */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-800">📊 Status</h2>
        
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600 font-medium">Selected User:</span>
            <span className="text-gray-800 font-semibold">
              {currentUser ? currentUser.user_id : '—'}
            </span>
          </div>

          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600 font-medium">Selected Block:</span>
            <span className="text-gray-800 font-semibold">
              {currentBlock ? currentBlock.name : '—'}
            </span>
          </div>

          <div className="flex items-center justify-between py-2">
            <span className="text-gray-600 font-medium">Session Status:</span>
            <span className={`font-semibold ${sessionId ? 'text-green-600' : 'text-gray-400'}`}>
              {sessionId ? '✅ Active' : '⏸️ Inactive'}
            </span>
          </div>

          {sessionId && (
            <div className="mt-4 p-3 bg-green-50 rounded-lg">
              <p className="text-xs text-green-700 font-mono break-all">
                Session ID: {sessionId}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  </div>

    {/* Modals - rendered outside the panel */}
    <MemoryViewer
      blockId={currentBlock?.meta_data?.id}
      isOpen={showMemoryViewer}
      onClose={() => setShowMemoryViewer(false)}
    />

    <SummaryViewer
      blockId={currentBlock?.meta_data?.id}
      isOpen={showSummaryViewer}
      onClose={() => setShowSummaryViewer(false)}
    />

    <ProcessingHistoryViewer
      sessionId={sessionId}
      isOpen={showProcessingHistory}
      onClose={() => setShowProcessingHistory(false)}
    />
  </>
  );
};

export default OptionsPanel;
