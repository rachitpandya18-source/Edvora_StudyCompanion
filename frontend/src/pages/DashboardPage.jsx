import { useState } from 'react';
import AppLayout from '../components/layout/AppLayout';
import QuickStartCard from '../components/dashboard/QuickStartCard';
import CourseCard from '../components/dashboard/CourseCard';
import StudyNextCard from '../components/dashboard/StudyNextCard';
import RecentActivity from '../components/dashboard/RecentActivity';
import LearningSnapshot from '../components/dashboard/LearningSnapshot';
import {
  mockStudentProfile,
  mockQuickStartActions,
  mockCourses,
  mockStudyNext,
  mockRecentActivity,
  mockOverallSnapshot,
} from '../data/mockDashboardData';

export default function DashboardPage({
  user = mockStudentProfile,
  courses = mockCourses,
  onNavigateToCourse,
  onEnterWorkspace,
  onCreateCourse,
}) {
  const [studyNext] = useState(mockStudyNext);
  const [activities] = useState(mockRecentActivity);
  const [snapshot] = useState(mockOverallSnapshot);
  const [notification, setNotification] = useState(null);

  const firstName = user?.name ? user.name.split(' ')[0] : 'Alex';

  const showToast = (msg) => {
    setNotification(msg);
    setTimeout(() => {
      setNotification(null);
    }, 3000);
  };

  const handleQuickAction = (action) => {
    if (action.id === 'continue') {
      if (onNavigateToCourse) {
        onNavigateToCourse(action.courseId, 'overview');
      } else if (onEnterWorkspace) {
        onEnterWorkspace(action.courseId);
      }
    } else if (action.id === 'tutor') {
      if (onNavigateToCourse) {
        onNavigateToCourse(action.courseId, 'tutor');
      } else if (onEnterWorkspace) {
        onEnterWorkspace(action.courseId);
      }
    } else if (action.id === 'practice') {
      if (onNavigateToCourse) {
        onNavigateToCourse(action.courseId, 'practice');
      } else if (onEnterWorkspace) {
        onEnterWorkspace(action.courseId);
      }
    } else if (action.id === 'materials') {
      if (onNavigateToCourse) {
        onNavigateToCourse(action.courseId, 'materials');
      } else if (onEnterWorkspace) {
        onEnterWorkspace(action.courseId);
      }
    }
  };

  const handleContinueCourse = (course) => {
    if (onNavigateToCourse) {
      onNavigateToCourse(course.id, 'overview');
    } else if (onEnterWorkspace) {
      onEnterWorkspace(course.id);
    }
  };

  const handleStartStudyNext = (item) => {
    if (onNavigateToCourse) {
      onNavigateToCourse(item.courseId, 'practice');
    } else if (onEnterWorkspace) {
      onEnterWorkspace(item.courseId);
    }
  };

  const handleViewCourse = (item) => {
    if (onNavigateToCourse) {
      onNavigateToCourse(item.courseId, 'overview');
    } else if (onEnterWorkspace) {
      onEnterWorkspace(item.courseId);
    }
  };

  const handleSidebarNavigate = (navId, extraData) => {
    if (navId === 'workspace' && extraData?.courseId) {
      if (onNavigateToCourse) {
        onNavigateToCourse(extraData.courseId, 'overview');
      } else if (onEnterWorkspace) {
        onEnterWorkspace(extraData.courseId);
      }
    } else if (navId === 'courses') {
      const coursesSection = document.getElementById('my-courses-section');
      if (coursesSection) {
        coursesSection.scrollIntoView({ behavior: 'smooth' });
      }
    } else if (navId === 'settings') {
      showToast('Settings panel will be available in the next release.');
    }
  };

  return (
    <AppLayout
      activeNav="home"
      user={user}
      recentCourses={courses}
      onNavigate={handleSidebarNavigate}
    >
      <div className="p-6 md:p-10 lg:p-12 space-y-10 max-w-7xl mx-auto">
        {/* Toast alert */}
        {notification && (
          <div className="fixed bottom-6 right-6 z-50 p-3.5 rounded-xl bg-[#18181c] border border-primary/50 text-white text-sm font-medium shadow-2xl flex items-center gap-2.5 animate-fade-in">
            <span className="material-symbols-outlined text-[18px] text-primary">info</span>
            <span>{notification}</span>
          </div>
        )}

        {/* 1. TOP HEADER */}
        <header className="pb-2 border-b border-[#222227]/70">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white leading-tight">
              Good morning, {firstName}.
            </h1>
            <p className="text-[#a1a1aa] text-base md:text-lg mt-1 font-normal">
              What would you like to learn today?
            </p>
          </div>
        </header>

        {/* 2. SECTION: QUICK START (4 Actions) */}
        <section aria-labelledby="quick-start-heading">
          <div className="flex items-center justify-between mb-4">
            <h2
              id="quick-start-heading"
              className="text-xs font-mono uppercase tracking-widest text-[#71717a] font-medium"
            >
              Quick start
            </h2>
            <span className="text-xs text-[#71717a] font-mono">1-click access</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {mockQuickStartActions.map((action) => (
              <QuickStartCard
                key={action.id}
                category={action.category}
                title={action.title}
                subtitle={action.subtitle}
                icon={action.icon}
                accent={action.accentColor}
                onClick={() => handleQuickAction(action)}
              />
            ))}
          </div>
        </section>

        {/* 3. MAIN TWO-COLUMN WORKSPACE: MY COURSES (LEFT) & STUDY NEXT + SNAPSHOT (RIGHT) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* LEFT COLUMN: MY COURSES & RECENT ACTIVITY (7 cols on desktop) */}
          <div id="my-courses-section" className="lg:col-span-7 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold tracking-tight text-white">My Courses</h2>
                <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-[#18181c] border border-[#222227] text-[#a1a1aa]">
                  {courses.length} Active
                </span>
              </div>

              {/* Create Course Action */}
              <button
                type="button"
                onClick={() => {
                  if (onCreateCourse) {
                    onCreateCourse();
                  } else {
                    showToast('Course creation wizard will be available in the next phase.');
                  }
                }}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#18181c] hover:bg-[#202026] border border-[#222227] text-white text-sm font-medium transition-all hover:border-[#a78bfa]/40 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[17px] text-primary">add</span>
                <span>Create Course</span>
              </button>
            </div>

            {/* Course Cards List */}
            <div className="space-y-4">
              {courses.map((course) => (
                <CourseCard
                  key={course.id}
                  course={course}
                  onContinue={handleContinueCourse}
                />
              ))}
            </div>

            {/* 5. RECENT ACTIVITY */}
            <RecentActivity activities={activities} />
          </div>

          {/* RIGHT COLUMN: STUDY NEXT & OVERALL SNAPSHOT (5 cols on desktop) */}
          <div className="lg:col-span-5 space-y-6">
            {/* 4. STUDY NEXT RECOMMENDATION */}
            <StudyNextCard
              studyNext={studyNext}
              onStart={handleStartStudyNext}
              onViewCourse={handleViewCourse}
            />

            {/* 6. OVERALL SNAPSHOT */}
            <LearningSnapshot snapshot={snapshot} />
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

