import { useState, useEffect, useCallback } from 'react';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import CreateCoursePage from './pages/CreateCoursePage';
import CourseWorkspacePage from './pages/CourseWorkspacePage';
import SettingsPage from './pages/SettingsPage';
import { getStoredToken, getStoredUser, clearAuthSession, normalizeUser } from './api/client';
import authApi from './api/authApi';
import coursesApi from './api/coursesApi';

function App() {
  const [currentUser, setCurrentUser] = useState(() => getStoredUser());
  const [currentView, setCurrentView] = useState(() => (getStoredToken() ? 'dashboard' : 'landing'));
  const [authMode, setAuthMode] = useState('login');
  const [courses, setCourses] = useState([]);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [activeCourseId, setActiveCourseId] = useState(null);
  const [activeCourseTitle, setActiveCourseTitle] = useState(null);
  const [activeSection, setActiveSection] = useState('overview');

  const fetchCourses = useCallback(async () => {
    setIsLoadingCourses(true);
    try {
      const data = await coursesApi.listCourses();
      const items = data?.items || [];
      const formatted = items.map((c) => ({
        id: c.id,
        code: c.title.slice(0, 6).toUpperCase(),
        title: c.title,
        category: c.description || 'Academic Study Course',
        mastery: 0,
        statusText: 'Active',
        statusVariant: 'developing',
        statusColor: '#a78bfa',
        currentlyLearning: c.sources?.[0]?.filename || 'Course Overview',
        lastStudied: 'Recently',
        materials: {
          textbooks: c.sources?.filter((s) => s.source_type === 'pdf').length || 0,
          slides: c.sources?.filter((s) => ['ppt', 'pptx'].includes(s.source_type)).length || 0,
          lectures: c.sources?.filter((s) => ['video', 'mp4'].includes(s.source_type)).length || 0,
        },
        primaryAction: 'Continue',
      }));
      setCourses(formatted);
    } catch {
      setCourses([]);
    } finally {
      setIsLoadingCourses(false);
    }
  }, []);

  // Validate session on mount
  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      authApi.getMe()
        .then((user) => {
          setCurrentUser(user);
        })
        .catch(() => {
          clearAuthSession();
          setCurrentUser(null);
          setCurrentView('landing');
        });
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    queueMicrotask(() => {
      if (ignore) return;
      if (currentUser) {
        fetchCourses();
      } else {
        setCourses([]);
      }
    });
    return () => {
      ignore = true;
    };
  }, [currentUser, fetchCourses]);



  const navigateToAuth = (mode = 'login') => {
    setAuthMode(mode);
    setCurrentView('auth');
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(normalizeUser(user));
    setCurrentView('dashboard');
    fetchCourses();
  };

  const handleLogout = () => {
    authApi.logout();
    setCurrentUser(null);
    setCurrentView('landing');
  };

  const handleNavigateToCourse = (courseId, tab = 'overview') => {
    setActiveCourseId(courseId);
    setActiveSection(tab);
    const found = courses.find((c) => c.id === courseId);
    if (found) {
      setActiveCourseTitle(found.title);
    }
    setCurrentView('workspace');
  };

  const handleCourseCreated = (createdCourse) => {
    fetchCourses().then(() => {
      const courseId = createdCourse?.id || `course-${Date.now()}`;
      const courseTitle = createdCourse?.title || createdCourse?.courseName || 'New Course';
      setActiveCourseId(courseId);
      setActiveCourseTitle(courseTitle);
      setActiveSection('overview');
      setCurrentView('workspace');
    });
  };

  const handleGlobalNavigate = (navId, extraData) => {
    if (navId === 'settings') {
      setCurrentView('settings');
    } else if (navId === 'create-course') {
      setCurrentView('create-course');
    } else if (navId === 'course' && extraData?.id) {
      setActiveCourseId(extraData.id);
      setActiveCourseTitle(extraData.title);
      setActiveSection(extraData.section || 'overview');
      setCurrentView('workspace');
    } else if (navId === 'home') {
      setCurrentView('dashboard');
    }
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

  const safeUser = normalizeUser(currentUser);

  if (currentView === 'dashboard') {
    return (
      <DashboardPage
        user={safeUser}
        courses={courses}
        isLoadingCourses={isLoadingCourses}
        onNavigate={handleGlobalNavigate}
        onNavigateToCourse={handleNavigateToCourse}
        onCreateCourse={() => setCurrentView('create-course')}
        onLogout={handleLogout}
        onEnterWorkspace={(courseId) => {
          const targetId = courseId || courses[0]?.id;
          if (!targetId) {
            setCurrentView('create-course');
            return;
          }
          setActiveCourseId(targetId);
          const found = courses.find((c) => c.id === targetId);
          if (found) {
            setActiveCourseTitle(found.title);
          }
          setCurrentView('workspace');
        }}
      />
    );
  }

  if (currentView === 'settings') {
    return (
      <SettingsPage
        user={safeUser}
        recentCourses={courses}
        onNavigate={handleGlobalNavigate}
        onBackToDashboard={() => setCurrentView('dashboard')}
        onLogout={handleLogout}
      />
    );
  }

  if (currentView === 'create-course') {
    return (
      <CreateCoursePage
        user={safeUser}
        recentCourses={courses}
        onBackToDashboard={() => setCurrentView('dashboard')}
        onCourseCreated={handleCourseCreated}
      />
    );
  }

  if (currentView === 'workspace') {
    return (
      <CourseWorkspacePage
        user={safeUser}
        courseId={activeCourseId}
        courseName={activeCourseTitle}
        recentCourses={courses}
        initialSection={activeSection}
        onBackToDashboard={() => setCurrentView('dashboard')}
        onCreateCourse={() => setCurrentView('create-course')}
        onNavigate={handleGlobalNavigate}
      />
    );
  }

  return (
    <LandingPage
      onNavigateToAuth={navigateToAuth}
      onEnterWorkspace={() => {
        if (currentUser) {
          setCurrentView('dashboard');
        } else {
          navigateToAuth('login');
        }
      }}
    />
  );
}

export default App;