import { useState } from 'react';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import StudyWorkspace from './components/StudyWorkspace';

function App() {
  const [currentView, setCurrentView] = useState('landing');
  const [authMode, setAuthMode] = useState('login');
  const [currentUser, setCurrentUser] = useState(null);
  const [activeCourseId, setActiveCourseId] = useState(null);

  const navigateToAuth = (mode = 'login') => {
    setAuthMode(mode);
    setCurrentView('auth');
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(user || { name: 'Alex Rivera', initials: 'AR', program: 'Computer Science' });
    setCurrentView('dashboard');
  };

  const handleNavigateToCourse = (courseId, _tab = 'overview') => {
    setActiveCourseId(courseId);
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

  if (currentView === 'dashboard') {
    return (
      <DashboardPage
        user={currentUser || { name: 'Alex Rivera', initials: 'AR', program: 'Computer Science' }}
        onNavigateToCourse={handleNavigateToCourse}
        onEnterWorkspace={(courseId) => {
          setActiveCourseId(courseId || 'cs201');
          setCurrentView('workspace');
        }}
      />
    );
  }

  if (currentView === 'workspace') {
    return (
      <StudyWorkspace
        currentUser={currentUser}
        courseId={activeCourseId}
        onBack={() => setCurrentView('dashboard')}
      />
    );
  }

  return (
    <LandingPage
      onNavigateToAuth={navigateToAuth}
      onEnterWorkspace={() => setCurrentView('dashboard')}
    />
  );
}

export default App;