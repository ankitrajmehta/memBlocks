import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../api/client';

const ProcessingHistoryViewer = ({ sessionId, isOpen, onClose }) => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedEvents, setExpandedEvents] = useState({});

  const fetchHistory = useCallback(async () => {
    if (!sessionId) return;
    try {
      setLoading(true);
      const data = await api.getProcessingHistory(sessionId);
      setEvents(data.events || []);
      setError(null);
    } catch (err) {
      if (err.message?.includes('not found')) {
        setEvents([]);
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!isOpen || !sessionId) return;

    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, [isOpen, sessionId, fetchHistory]);

  const toggleEvent = (eventId) => {
    setExpandedEvents((prev) => ({
      ...prev,
      [eventId]: !prev[eventId]
    }));
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getOperationColor = (operation) => {
    switch (operation) {
      case 'ADD': return 'text-green-600 bg-green-50 border-green-200';
      case 'UPDATE': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'DELETE': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getOperationIcon = (operation) => {
    switch (operation) {
      case 'ADD': return '✅';
      case 'UPDATE': return '🔄';
      case 'DELETE': return '❌';
      default: return '⏭️';
    }
  };

  const countOperations = (operations) => {
    const counts = { ADD: 0, UPDATE: 0, DELETE: 0, NONE: 0 };
    operations.forEach((op) => {
      if (counts.hasOwnProperty(op.operation)) {
        counts[op.operation]++;
      }
    });
    return counts;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-800">⚙️ Processing History</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading && events.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          ) : events.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <div className="text-6xl mb-4">📭</div>
              <p className="text-lg">No processing events yet</p>
              <p className="text-sm mt-2">Events appear when memory window processing triggers (after {10} messages)</p>
            </div>
          ) : (
            <div className="space-y-4">
              {events.map((event, index) => {
                const counts = countOperations(event.operations);
                const isExpanded = expandedEvents[event.event_id];

                return (
                  <div
                    key={event.event_id}
                    className="border border-gray-200 rounded-lg overflow-hidden"
                  >
                    <button
                      onClick={() => toggleEvent(event.event_id)}
                      className="w-full p-4 bg-gray-50 hover:bg-gray-100 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-4">
                        <span className="text-lg font-semibold text-gray-800">
                          Event #{events.length - index}
                        </span>
                        <span className="text-sm text-gray-500">
                          🕐 {formatTimestamp(event.timestamp)}
                        </span>
                        <span className="text-sm text-gray-500">
                          📨 {event.messages_processed} messages
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {counts.ADD > 0 && (
                          <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                            +{counts.ADD}
                          </span>
                        )}
                        {counts.UPDATE > 0 && (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs">
                            ↻{counts.UPDATE}
                          </span>
                        )}
                        {counts.DELETE > 0 && (
                          <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs">
                            -{counts.DELETE}
                          </span>
                        )}
                        <span className="text-gray-400 ml-2">
                          {isExpanded ? '▼' : '▶'}
                        </span>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="p-4 border-t border-gray-200 bg-white">
                        <div className="space-y-3">
                          {event.operations
                            .filter((op) => op.operation !== 'NONE')
                            .map((op, opIndex) => (
                              <div
                                key={opIndex}
                                className={`p-3 rounded-lg border ${getOperationColor(op.operation)}`}
                              >
                                <div className="flex items-center gap-2 mb-2">
                                  <span>{getOperationIcon(op.operation)}</span>
                                  <span className="font-semibold uppercase text-sm">
                                    {op.operation}
                                  </span>
                                  {op.memory_id && (
                                    <span className="text-xs opacity-60 font-mono">
                                      ID: {op.memory_id.slice(0, 8)}...
                                    </span>
                                  )}
                                </div>
                                {op.operation === 'UPDATE' && op.old_content && (
                                  <div className="mb-2 p-2 bg-white bg-opacity-50 rounded text-sm">
                                    <div className="text-xs text-gray-500 mb-1">Previous:</div>
                                    <div className="line-through text-gray-500">{op.old_content}</div>
                                  </div>
                                )}
                                <div className="text-sm">
                                  {op.content}
                                </div>
                              </div>
                            ))}
                          {event.operations.filter((op) => op.operation !== 'NONE').length === 0 && (
                            <div className="text-center text-gray-500 py-4">
                              No significant operations (all were redundant)
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 p-4 flex justify-between items-center">
          <div className="text-sm text-gray-500">
            {events.length} event{events.length !== 1 ? 's' : ''} • Auto-refresh every 5s
          </div>
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

export default ProcessingHistoryViewer;
