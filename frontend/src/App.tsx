/** Root App component with routing. */

import { useState, useEffect } from 'react';
import { FaceLogin } from './components/FaceLogin';
import { FaceEnroll } from './components/FaceEnroll';
import { Dashboard } from './components/Dashboard';
import { useAuthStore } from './store/authStore';
import type { AppView } from './types';

export default function App() {
  const { isAuthenticated, restoreSession } = useAuthStore();
  const [view, setView] = useState<AppView>('login');
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    restoreSession().finally(() => setInitialized(true));
  }, [restoreSession]);

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 mx-auto border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400">Initializing Face ID...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Dashboard />;
  }

  if (view === 'enroll') {
    return <FaceEnroll onSwitchToLogin={() => setView('login')} />;
  }

  return <FaceLogin onSwitchToEnroll={() => setView('enroll')} />;
}
