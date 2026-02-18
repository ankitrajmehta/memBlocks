import React, { useState, useEffect } from 'react';
import * as api from '../api/client';

/**
 * UserSelector Component
 * Handles user selection and creation
 */
const UserSelector = ({ currentUser, onUserSelect }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newUserId, setNewUserId] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Load users on mount
  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const fetchedUsers = await api.listUsers();
      setUsers(fetchedUsers);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUserId.trim()) {
      setError('User ID cannot be empty');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const createdUser = await api.createUser(newUserId.trim());
      setUsers([...users, createdUser]);
      onUserSelect(createdUser);
      setNewUserId('');
      setShowCreateForm(false);
    } catch (err) {
      setError(err.message);
      console.error('Failed to create user:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectUser = (e) => {
    const userId = e.target.value;
    if (userId) {
      const user = users.find(u => u.user_id === userId);
      onUserSelect(user);
    } else {
      onUserSelect(null);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-4">
      <h2 className="text-xl font-bold mb-4 text-gray-800">👤 User Selection</h2>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* User Selection Dropdown */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select User
        </label>
        <select
          value={currentUser?.user_id || ''}
          onChange={handleSelectUser}
          disabled={loading}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
        >
          <option value="">-- Select a user --</option>
          {users.map((user) => (
            <option key={user.user_id} value={user.user_id}>
              {user.user_id}
            </option>
          ))}
        </select>
      </div>

      {/* Create New User Toggle */}
      <button
        onClick={() => setShowCreateForm(!showCreateForm)}
        className="text-primary-600 hover:text-primary-700 text-sm font-medium mb-4"
      >
        {showCreateForm ? '− Cancel' : '+ Create New User'}
      </button>

      {/* Create User Form */}
      {showCreateForm && (
        <form onSubmit={handleCreateUser} className="mt-4 p-4 bg-gray-50 rounded-md">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            New User ID
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={newUserId}
              onChange={(e) => setNewUserId(e.target.value)}
              placeholder="e.g., john_doe"
              disabled={loading}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
            />
            <button
              type="submit"
              disabled={loading || !newUserId.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      )}

      {loading && (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
        </div>
      )}
    </div>
  );
};

export default UserSelector;
