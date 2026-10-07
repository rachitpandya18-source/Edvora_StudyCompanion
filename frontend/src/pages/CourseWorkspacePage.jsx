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
          <div className="rounded-xl border border-[#222227] bg-[#121215] p-8 sm:p-12 text-center max-w-2xl mx-auto space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-[#a1a1aa]/10 border border-[#a1a1aa]/20 text-[#a1a1aa] flex items-center justify-center mx-auto">
              <span className="material-symbols-outlined text-[32px]">folder_copy</span>
            </div>
            <h3 className="text-2xl font-bold text-white tracking-tight">Course Materials</h3>
            <p className="text-[15px] text-[#a1a1aa] leading-relaxed">
              Your uploaded PDFs, lecture slides, and videos organized with concept extraction.
            </p>
            <div className="pt-4 flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setActiveSection('overview')}
                className="px-4 py-2 rounded-lg bg-[#18181c] border border-[#2e2e36] text-sm font-medium text-white hover:bg-[#222227] transition-colors cursor-pointer"
              >
                Back to Overview
              </button>
            </div>
          </div>
        );

      case 'progress':
        return (
          <div className="rounded-xl border border-[#222227] bg-[#121215] p-8 sm:p-12 text-center max-w-2xl mx-auto space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-[#fbbf24]/10 border border-[#fbbf24]/20 text-[#fbbf24] flex items-center justify-center mx-auto">
              <span className="material-symbols-outlined text-[32px]">trending_up</span>
            </div>
            <h3 className="text-2xl font-bold text-white tracking-tight">Learning Progress</h3>
            <p className="text-[15px] text-[#a1a1aa] leading-relaxed">
              Detailed breakdown of your topic mastery, study trajectory, and knowledge progression.
            </p>
            <div className="pt-4 flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setActiveSection('overview')}
                className="px-4 py-2 rounded-lg bg-[#18181c] border border-[#2e2e36] text-sm font-medium text-white hover:bg-[#222227] transition-colors cursor-pointer"
              >
                Back to Overview
              </button>
            </div>
          </div>
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
