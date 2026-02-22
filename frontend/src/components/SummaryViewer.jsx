import React, { useState } from 'react';
import * as api from '../api/client';

/**
 * SummaryViewer Component
 * Displays recursive summary in a modal
 */
const SummaryViewer = ({ blockId, isOpen, onClose }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load summary when modal opens
  React.useEffect(() => {
    if (isOpen && blockId) {
      loadSummary();
    }
  }, [isOpen, blockId]);

  const loadSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getRecursiveSummary(blockId);
      setSummary(data);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load recursive summary:', err);
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
          <h2 className="text-2xl font-bold text-gray-800">📚 Recursive Summary</h2>
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
          ) : summary ? (
            <div className="space-y-4">
              {/* Display summary text */}
              {summary.summary ? (
                <div className="bg-gray-50 rounded-lg p-6">
                  <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {summary.summary}
                  </p>
                </div>
              ) : summary.recursive_summary ? (
                <div className="bg-gray-50 rounded-lg p-6">
                  <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                    {summary.recursive_summary}
                  </p>
                </div>
              ) : summary.message ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-6xl mb-4">📝</div>
                  <p className="text-lg">{summary.message}</p>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-6xl mb-4">📝</div>
                  <p className="text-lg">No summary available yet</p>
                  <p className="text-sm mt-2">Summaries are generated as conversations progress</p>
                </div>
              )}

              {/* Level information if available */}
              {summary.level !== undefined && (
                <div className="bg-primary-50 rounded-lg p-4 text-sm">
                  <p className="text-primary-700">
                    <span className="font-semibold">Summary Level:</span> {summary.level}
                  </p>
                </div>
              )}

              {/* Timestamp if available */}
              {summary.created_at && (
                <div className="text-sm text-gray-500">
                  <span className="font-semibold">Created:</span>{' '}
                  {new Date(summary.created_at).toLocaleString()}
                </div>
              )}

              {/* Metadata */}
              {summary.metadata && (
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <h3 className="font-semibold text-gray-700 mb-2">Metadata</h3>
                  <div className="bg-gray-50 rounded-lg p-4 text-sm">
                    <pre className="whitespace-pre-wrap text-gray-600">
                      {JSON.stringify(summary.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <div className="text-6xl mb-4">📭</div>
              <p className="text-lg">No summary data available</p>
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

export default SummaryViewer;
