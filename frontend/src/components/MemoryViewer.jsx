import React, { useState } from 'react';
import * as api from '../api/client';

/**
 * MemoryViewer Component
 * Displays core memory in a modal
 */
const MemoryViewer = ({ blockId, isOpen, onClose }) => {
  const [memory, setMemory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load memory when modal opens
  React.useEffect(() => {
    if (isOpen && blockId) {
      loadMemory();
    }
  }, [isOpen, blockId]);

  const loadMemory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCoreMemory(blockId);
      setMemory(data);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load core memory:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-800">🧠 Core Memory</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          ) : memory ? (
            <div className="space-y-4">
              {/* Display memory contents */}
              {memory.persona_content || memory.human_content ? (
                <div className="space-y-4">
                  {memory.persona_content && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-700 mb-2">Persona Content</h3>
                      <p className="text-gray-600 whitespace-pre-wrap">{memory.persona_content}</p>
                    </div>
                  )}
                  {memory.human_content && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-700 mb-2">Human Content</h3>
                      <p className="text-gray-600 whitespace-pre-wrap">{memory.human_content}</p>
                    </div>
                  )}
                </div>
              ) : memory.core_memory && typeof memory.core_memory === 'object' ? (
                <div className="space-y-4">
                  {Object.entries(memory.core_memory).map(([key, value]) => (
                    <div key={key} className="bg-gray-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-700 mb-2 capitalize">
                        {key.replace(/_/g, ' ')}
                      </h3>
                      <p className="text-gray-600 whitespace-pre-wrap">{value}</p>
                    </div>
                  ))}
                </div>
              ) : memory.core_memory && typeof memory.core_memory === 'string' ? (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-600 whitespace-pre-wrap">{memory.core_memory}</p>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-6xl mb-4">📭</div>
                  <p className="text-lg">No core memory found for this block</p>
                  <p className="text-sm mt-2">Core memory is built over time through conversations</p>
                </div>
              )}

              {/* Metadata */}
              {memory.created_at && (
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <h3 className="font-semibold text-gray-700 mb-2">Metadata</h3>
                  <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
                    <p><span className="font-medium">Block ID:</span> {memory.block_id}</p>
                    {memory.created_at && <p><span className="font-medium">Created:</span> {memory.created_at}</p>}
                    {memory.updated_at && <p><span className="font-medium">Updated:</span> {memory.updated_at}</p>}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <div className="text-6xl mb-4">📭</div>
              <p className="text-lg">No memory data available</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default MemoryViewer;
