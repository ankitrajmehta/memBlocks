import React, { useState, useEffect, useRef } from 'react';
import * as api from '../api/client';

/**
 * ChatPanel Component
 * Displays chat messages and handles user input
 */
const ChatPanel = ({ sessionId, currentUser, currentBlock }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat history when session changes
  useEffect(() => {
    if (sessionId) {
      loadChatHistory();
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  const loadChatHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const history = await api.getChatHistory(sessionId);
      
      // Transform history into messages array
      const formattedMessages = [];
      const messages = history?.conversation_history || history?.messages || [];
      messages.forEach((msg) => {
        if (msg.role === 'user') {
          formattedMessages.push({
            role: 'user',
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString(),
          });
        } else if (msg.role === 'assistant') {
          formattedMessages.push({
            role: 'assistant',
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString(),
          });
        }
      });
      setMessages(formattedMessages);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load chat history:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || !sessionId) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');

    // Add user message to UI immediately
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newUserMessage]);

    try {
      setLoading(true);
      setError(null);
      
      // Send message to backend
      const response = await api.sendMessage(sessionId, userMessage);
      
      // Add assistant response to UI
      const assistantMessage = {
        role: 'assistant',
        content: response.ai_response || response.response || response.message || 'No response',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message);
      console.error('Failed to send message:', err);
      
      // Add error message to chat
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          content: `Error: ${err.message}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-lg shadow-md">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 text-white px-6 py-4 rounded-t-lg">
        <h2 className="text-xl font-bold mb-1">💬 Chat Interface</h2>
        {currentUser && currentBlock ? (
          <div className="text-sm opacity-90">
            <span className="font-medium">{currentUser.user_id}</span>
            <span className="mx-2">•</span>
            <span>{currentBlock.name}</span>
          </div>
        ) : (
          <div className="text-sm opacity-75 italic">
            No active session
          </div>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {!sessionId ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-6xl mb-4">🤖</div>
              <p className="text-lg">Select a user and block, then start a session to begin chatting</p>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-6xl mb-4">👋</div>
              <p className="text-lg">No messages yet. Start the conversation!</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : message.role === 'system'
                    ? 'bg-red-100 text-red-700 border border-red-200'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <div className="whitespace-pre-wrap break-words">{message.content}</div>
                <div
                  className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-primary-200' : 'text-gray-500'
                  }`}
                >
                  {formatTimestamp(message.timestamp)}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-6 pb-2">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSendMessage} className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={sessionId ? "Type your message..." : "Start a session to chat"}
            disabled={!sessionId || loading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!sessionId || loading || !inputMessage.trim()}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {loading ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Sending...</span>
              </div>
            ) : (
              '📤 Send'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;
