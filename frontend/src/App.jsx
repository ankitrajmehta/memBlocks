import React from 'react';
import { useAuth, useUser } from '@clerk/react';
import { Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
import Workspace from './pages/Workspace';

function App() {
  const { isLoaded, userId } = useAuth();
  const { user, isLoaded: userLoaded } = useUser();

  if (!isLoaded || !userLoaded) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!userId) {
    return <Landing />;
  }

  return <Workspace />;
}

export default App;
