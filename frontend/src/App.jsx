import { useState, useEffect, useCallback } from 'react';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import CreateCoursePage from './pages/CreateCoursePage';
import CourseWorkspacePage from './pages/CourseWorkspacePage';
import { getStoredToken, getStoredUser, clearAuthSession } from './api/client';
import authApi from './api/authApi';
import coursesApi from './api/coursesApi';
import { mockCourses } from './data/mockDashboardData';

function App() {
  const [currentUser, setCurrentUser] = useState(() => getStoredUser());
  const [currentView, setCurrentView] = useState(() => (getStoredToken() ? 'dashboard' : 'landing'));
  const [authMode, setAuthMode] = useState('login');
  const [courses, setCourses] = useState([]);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [activeCourseId, setActiveCourseId] = useState(null);
  const [activeCourseTitle, setActiveCourseTitle] = useState(null);

  const fetchCourses = useCallback(async () => {
    setIsLoadingCourses(true);
    try {
      const data = await coursesApi.listCourses();
      const items = data?.items || [];
      if (items.length > 0) {
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
      } else {
        setCourses(mockCourses);
      }
    } catch {
      setCourses(mockCourses);
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
    async function load() {
      if (currentUser) {
        setIsLoadingCourses(true);
        try {
          const data = await coursesApi.listCourses();
          if (ignore) return;
          const items = data?.items || [];
          if (items.length > 0) {
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
          } else {
            setCourses(mockCourses);
          }
        } catch {
          if (!ignore) setCourses(mockCourses);
        } finally {
          if (!ignore) setIsLoadingCourses(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [currentUser]);



  const navigateToAuth = (mode = 'login') => {
    setAuthMode(mode);
    setCurrentView('auth');
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(user || { name: 'Alex Rivera', initials: 'AR', program: 'Computer Science' });
    setCurrentView('dashboard');
    fetchCourses();
  };

  const handleLogout = () => {
    authApi.logout();
    setCurrentUser(null);
    setCurrentView('landing');
  };

  const handleNavigateToCourse = (courseId, _tab = 'overview') => {
    setActiveCourseId(courseId);
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
      setCurrentView('workspace');
    });
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
        isLoadingCourses={isLoadingCourses}
        onNavigateToCourse={handleNavigateToCourse}
        onCreateCourse={() => setCurrentView('create-course')}
        onLogout={handleLogout}
        onEnterWorkspace={(courseId) => {
          const targetId = courseId || courses[0]?.id || 'cs201';
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