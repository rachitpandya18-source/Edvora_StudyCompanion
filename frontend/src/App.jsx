import { useState } from 'react';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import StudyWorkspace from './components/StudyWorkspace';

function App() {
  const [currentView, setCurrentView] = useState('landing');
  const [authMode, setAuthMode] = useState('login');
  const [currentUser, setCurrentUser] = useState(null);

  const navigateToAuth = (mode = 'login') => {
    setAuthMode(mode);
    setCurrentView('auth');
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    setCurrentView('workspace');
  };

  if (currentView === 'auth') {
    return (
      <AuthPage
        initialMode={authMode}
        onBackToLanding={() => setCurrentView('landing')}
        onAuthSuccess={handleAuthSuccess}
      />
    );
  }

  if (currentView === 'workspace') {
    return (
      <StudyWorkspace
        currentUser={currentUser}
        onBack={() => setCurrentView('landing')}
      />
    );
  }

  return (
    <LandingPage
      onNavigateToAuth={navigateToAuth}
      onEnterWorkspace={() => setCurrentView('workspace')}
    />
  );
}

export default App;