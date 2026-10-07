import { useState } from 'react';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import CreateCoursePage from './pages/CreateCoursePage';
import CourseWorkspacePage from './pages/CourseWorkspacePage';
import { mockCourses } from './data/mockDashboardData';

function App() {
  const [currentView, setCurrentView] = useState('landing');
  const [authMode, setAuthMode] = useState('login');
  const [currentUser, setCurrentUser] = useState(null);
  const [courses, setCourses] = useState(mockCourses);
  const [activeCourseId, setActiveCourseId] = useState(null);
  const [activeCourseTitle, setActiveCourseTitle] = useState(null);

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
    const found = courses.find((c) => c.id === courseId);
    if (found) {
      setActiveCourseTitle(found.title);
    }
    setCurrentView('workspace');
  };

  const handleCourseCreated = ({ courseName, description, materials }) => {
    const newCourse = {
      id: `course-${Date.now()}`,
      code: courseName.slice(0, 6).toUpperCase(),
      title: courseName,
      category: description || 'Personal Study Course',
      mastery: 0,
      statusText: 'New',
      statusVariant: 'developing',
      statusColor: '#a78bfa',
      currentlyLearning: materials?.[0]?.name || 'Introduction',
      lastStudied: 'Just now',
      materials: {
        textbooks: materials?.filter((m) => m.type === 'pdf').length || 0,
        slides: materials?.filter((m) => m.type === 'pptx' || m.type === 'ppt').length || 0,
        lectures: materials?.filter((m) => m.type === 'video').length || 0,
      },
      primaryAction: 'Continue',
    };

    setCourses((prev) => [newCourse, ...prev]);
    setActiveCourseId(newCourse.id);
    setActiveCourseTitle(newCourse.title);
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
        courses={courses}
        onNavigateToCourse={handleNavigateToCourse}
        onCreateCourse={() => setCurrentView('create-course')}
        onEnterWorkspace={(courseId) => {
          setActiveCourseId(courseId || 'cs201');
          const found = courses.find((c) => c.id === (courseId || 'cs201'));
          if (found) {
            setActiveCourseTitle(found.title);
          }
          setCurrentView('workspace');
        }}
      />
    );
  }

  if (currentView === 'create-course') {
    return (
      <CreateCoursePage
        user={currentUser || { name: 'Alex Rivera', initials: 'AR', program: 'Computer Science' }}
        recentCourses={courses}
        onBackToDashboard={() => setCurrentView('dashboard')}
        onCourseCreated={handleCourseCreated}
      />
    );
  }

  if (currentView === 'workspace') {
    return (
      <CourseWorkspacePage
        user={currentUser || { name: 'Alex Rivera', initials: 'AR', program: 'Computer Science' }}
        courseId={activeCourseId}
        courseName={activeCourseTitle}
        recentCourses={courses}
        onBackToDashboard={() => setCurrentView('dashboard')}
        onCreateCourse={() => setCurrentView('create-course')}
        onNavigate={(navId, extraData) => {
          if (navId === 'create-course') {
            setCurrentView('create-course');
          } else if (navId === 'course' && extraData?.id) {
            setActiveCourseId(extraData.id);
            setActiveCourseTitle(extraData.title);
            setCurrentView('workspace');
          } else if (navId === 'home') {
            setCurrentView('dashboard');
          }
        }}
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