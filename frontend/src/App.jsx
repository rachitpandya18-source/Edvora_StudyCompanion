import { useState } from 'react';
import LandingPage from './pages/LandingPage';
import StudyWorkspace from './components/StudyWorkspace';

function App() {
  const [currentView, setCurrentView] = useState('landing');

  if (currentView === 'workspace') {
    return <StudyWorkspace onBack={() => setCurrentView('landing')} />;
  }

  return (
    <LandingPage onEnterWorkspace={() => setCurrentView('workspace')} />
  );
}

export default App;