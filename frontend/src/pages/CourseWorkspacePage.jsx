import React, { useState, useEffect } from 'react';
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
import curriculumApi from '../api/curriculumApi';
import analyticsApi from '../api/analyticsApi';
import { defaultCourseOverviewData } from '../data/mockCourseOverviewData';

/**
 * CourseWorkspacePage
 * Edvora Course Workspace Shell and Course Overview page.
 */
export default function CourseWorkspacePage({
  user,
  courseId,
  courseName,
  recentCourses = [],
  initialSection = 'overview',
  onBackToDashboard,
  onCreateCourse,
  onNavigate,
}) {
  const [activeSection, setActiveSection] = useState(initialSection);
  const [liveOverview, setLiveOverview] = useState(null);
  const [liveStudyNext, setLiveStudyNext] = useState(null);
  const [hasCurriculum, setHasCurriculum] = useState(true);

  // Fetch real curriculum, study-next recommendation, and analytics overview
  useEffect(() => {
    if (!courseId) return;

    // Fetch curriculum status
    curriculumApi.getCurriculum(courseId)
      .then((curr) => {
        if (curr?.topics && curr.topics.length > 0) {
          setHasCurriculum(true);
        } else {
          setHasCurriculum(false);
        }
      })
      .catch(() => {
        setHasCurriculum(false);
      });

    // Fetch top study recommendation
    curriculumApi.getStudyNext(courseId)
      .then((topRec) => {
        if (topRec) {
          setLiveStudyNext({
            topic: topRec.concept_title || topRec.concept_id,
            headline: topRec.reason || 'Recommended next concept based on prerequisite readiness',
            readiness: 'Optimal',
            actionText: 'Start Session',
            reason: `Prerequisite depth ${topRec.prerequisite_depth}. Target mastery threshold 0.85.`,
            estimatedMinutes: 10,
          });
        }
      })
      .catch(() => {});

    // Fetch analytics overview
    analyticsApi.getOverview(courseId)
      .then((ov) => {
        if (ov) {
          setLiveOverview(ov);
        }
      })
      .catch(() => {});
  }, [courseId]);

  // Merge default data with real backend attributes
  const courseData = {
    ...defaultCourseOverviewData,
    courseName: courseName || defaultCourseOverviewData.courseName,
    mastery: liveOverview ? Math.round(liveOverview.overall_mastery * 100) : defaultCourseOverviewData.mastery,
    studyNext: liveStudyNext || defaultCourseOverviewData.studyNext,
  };

  const handleGlobalNav = (navId, extraData) => {
    if (navId === 'home') {
      onBackToDashboard?.();
    } else if (navId === 'create-course') {
      onCreateCourse?.();
    } else if (navId === 'course-item' && extraData?.id) {
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
            {!hasCurriculum && (
              <div className="p-5 rounded-xl bg-[#18181b] border border-[#a78bfa]/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px] text-[#a78bfa]">auto_awesome</span>
                    Ready for Curriculum Generation
                  </h4>
                  <p className="text-xs text-[#a1a1aa]">
                    Upload course lecture notes or textbooks to automatically extract topics, concepts, and knowledge graph prerequisites.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveSection('materials')}
                  className="px-4 py-2 rounded-lg bg-[#a78bfa] text-black font-semibold text-xs hover:bg-[#c4b5fd] transition-colors shrink-0 cursor-pointer"
                >
                  Upload Materials
                </button>
              </div>
            )}

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
            courseId={courseId}
            courseName={courseData.courseName}
          />
        );

      case 'practice':
        return (
          <CoursePracticePage
            courseId={courseId}
            courseName={courseData.courseName}
          />
        );

      case 'materials':
        return (
          <CourseMaterialsPage
            courseId={courseId}
            courseName={courseData.courseName}
            onCurriculumGenerated={() => {
              setHasCurriculum(true);
              setActiveSection('overview');
            }}
          />
        );

      case 'progress':
        return (
          <CourseProgressPage
            courseId={courseId}
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
