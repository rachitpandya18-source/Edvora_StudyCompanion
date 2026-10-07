import React, { useState } from 'react';
import AppLayout from '../components/layout/AppLayout';
import CourseHeader from '../components/course/CourseHeader';
import CourseNavigation from '../components/course/CourseNavigation';
import CourseStudyNext from '../components/course/CourseStudyNext';
import CourseMasteryList from '../components/course/CourseMasteryList';
import CourseQuickActions from '../components/course/CourseQuickActions';
import LearningMapPreview from '../components/course/LearningMapPreview';
import CourseRecentActivity from '../components/course/CourseRecentActivity';
import CourseTutorView from '../components/tutor/CourseTutorView';
import CoursePracticePage from './CoursePracticePage';
import CourseMaterialsPage from './CourseMaterialsPage';
import CourseProgressPage from './CourseProgressPage';
import { defaultCourseOverviewData } from '../data/mockCourseOverviewData';

/**
 * CourseWorkspacePage
 * Edvora Course Workspace Shell and Course Overview page.
 */
export default function CourseWorkspacePage({
  user,
  _courseId,
  courseName,
  recentCourses = [],
  initialSection = 'overview',
  onBackToDashboard,
  onCreateCourse,
  onNavigate,
}) {
  const [activeSection, setActiveSection] = useState(initialSection);

  // Merge default mock data with dynamic course name if provided
  const courseData = {
    ...defaultCourseOverviewData,
    courseName: courseName || defaultCourseOverviewData.courseName,
  };

  const handleGlobalNav = (navId, extraData) => {
    if (navId === 'home') {
      onBackToDashboard?.();
    } else if (navId === 'create-course') {
      onCreateCourse?.();
    } else if (navId === 'course-item' && extraData?.id) {
      // Navigate to another course if clicked in sidebar
      onNavigate?.('course', extraData);
    } else {
      onNavigate?.(navId, extraData);
    }
  };

  const renderSectionContent = () => {
    switch (activeSection) {
      case 'overview':
        return (
          <div className="space-y-8">
            {/* 1. FULL WIDTH: STUDY NEXT */}
            <CourseStudyNext
              studyNext={courseData.studyNext}
              onStartSession={() => setActiveSection('practice')}
              onViewTopic={() => setActiveSection('materials')}
            />

            {/* 2. TWO-COLUMN ROW: MASTERY + QUICK ACTIONS */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              <div className="lg:col-span-7">
                <CourseMasteryList topics={courseData.topics} />
              </div>
              <div className="lg:col-span-5">
                <CourseQuickActions
                  onSelectAction={(targetSection) => setActiveSection(targetSection)}
                />
              </div>
            </div>

            {/* 3. TWO-COLUMN ROW: LEARNING MAP + RECENT ACTIVITY */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              <LearningMapPreview
                learningMap={courseData.learningMap}
                onOpenLearningMap={() => setActiveSection('progress')}
              />
              <CourseRecentActivity activities={courseData.recentActivity} />
            </div>
          </div>
        );

      case 'tutor':
        return (
          <CourseTutorView
            user={user}
            courseName={courseData.courseName}
          />
        );

      case 'practice':
        return (
          <CoursePracticePage
            courseName={courseData.courseName}
          />
        );

      case 'materials':
        return (
          <CourseMaterialsPage
            courseName={courseData.courseName}
          />
        );

      case 'progress':
        return (
          <CourseProgressPage
            courseName={courseData.courseName}
            onNavigateToPractice={() => setActiveSection('practice')}
            onNavigateToTutor={() => setActiveSection('tutor')}
          />
        );

      default:
        return null;
    }
  };

  return (
    <AppLayout
      activeNav="courses"
      onNavigate={handleGlobalNav}
      user={user}
      recentCourses={recentCourses}
    >
      <div className="p-6 sm:p-8 lg:p-10 max-w-7xl mx-auto w-full">
        {/* Course Header */}
        <CourseHeader
          courseName={courseData.courseName}
          mastery={courseData.mastery}
          weakestTopic={activeSection === 'practice' ? { name: 'AVL Trees', mastery: 43 } : null}
          onBack={onBackToDashboard}
        />

        {/* 5-Tab Navigation */}
        <CourseNavigation
          activeSection={activeSection}
          onSelectSection={setActiveSection}
        />

        {/* Main Section Content */}
        {renderSectionContent()}
      </div>
    </AppLayout>
  );
}
