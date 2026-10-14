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
  const [prevInitialSection, setPrevInitialSection] = useState(initialSection);
  const [liveOverview, setLiveOverview] = useState(null);
  const [liveStudyNext, setLiveStudyNext] = useState(null);
  const [liveTopics, setLiveTopics] = useState([]);
  const [hasCurriculum, setHasCurriculum] = useState(true);
  const [isGeneratingCurriculum, setIsGeneratingCurriculum] = useState(false);
  const [curriculumMessage, setCurriculumMessage] = useState(null);

  if (initialSection !== prevInitialSection) {
    setPrevInitialSection(initialSection);
    setActiveSection(initialSection);
  }

  // Fetch real curriculum, study-next recommendation, and analytics overview
  useEffect(() => {
    if (!courseId) return;

    // Fetch curriculum status
    curriculumApi.getCurriculum(courseId)
      .then((curr) => {
        if (curr?.topics && curr.topics.length > 0) {
          setHasCurriculum(true);
          const mapped = curr.topics.map((t, idx) => ({
            id: t.id || `topic-${idx}`,
            name: t.title,
            percentage: 0,
            status: 'Developing',
            variant: 'developing',
            isStudyNext: idx === 0,
          }));
          setLiveTopics(mapped);
        } else {
          setHasCurriculum(false);
          setLiveTopics([]);
        }
      })
      .catch(() => {
        setHasCurriculum(false);
        setLiveTopics([]);
      });

    // Fetch top study recommendation
    curriculumApi.getStudyNext(courseId)
      .then((topRec) => {
        if (topRec) {
          const displayTopic = topRec.concept_name || topRec.topic_title || topRec.concept_title || 'Core Curriculum';
          const displayRationale = topRec.rationale || topRec.reason || 'Recommended next concept based on prerequisite readiness.';
          const masteryPct = Math.round((topRec.mastery_probability ?? 0) * 100);
          const prerequisiteNote = topRec.prerequisite_depth != null
            ? `Prerequisite depth ${topRec.prerequisite_depth}. Target mastery threshold 85%.`
            : topRec.unblocked_dependents_count
            ? `Mastering this unblocks ${topRec.unblocked_dependents_count} dependent concepts in this course.`
            : 'Core curriculum readiness. Target mastery threshold 85%.';

          setLiveStudyNext({
            topic: displayTopic,
            mastery: masteryPct,
            statusText: topRec.status_text || 'Recommended',
            headline: displayRationale,
            whyThis: `${displayRationale} ${prerequisiteNote}`,
            actionText: 'Start Session',
            reason: prerequisiteNote,
            estimatedMinutes: 10,
            recommendedActions: topRec.recommended_actions?.length
              ? topRec.recommended_actions.map((act) => ({
                  id: String(act.step),
                  icon: act.action_type === 'practice_quiz' ? 'fact_check' : act.action_type === 'ask_tutor' ? 'chat' : 'menu_book',
                  title: act.title,
                }))
              : undefined,
          });
        }
      })
      .catch(() => {});

    // Fetch analytics overview
    analyticsApi.getOverview(courseId)
      .then((ov) => {
        if (ov) {
          setLiveOverview(ov);
          if (ov.topic_summaries && ov.topic_summaries.length > 0) {
            const mapped = ov.topic_summaries.map((ts, idx) => ({
              id: ts.topic_id || `topic-${idx}`,
              name: ts.title,
              percentage: Math.round(ts.average_mastery * 100),
              status: ts.status === 'mastered' ? 'Mastered' : ts.status === 'proficient' ? 'Proficient' : 'Developing',
              variant: ts.status === 'mastered' ? 'strong' : ts.status === 'proficient' ? 'developing' : 'attention',
              isStudyNext: idx === 0,
            }));
            setLiveTopics(mapped);
          }
        }
      })
      .catch(() => {});
  }, [courseId]);

  const handleTriggerGenerateCurriculum = async () => {
    if (!courseId || isGeneratingCurriculum) return;
    setIsGeneratingCurriculum(true);
    setCurriculumMessage('Generating curriculum from course materials...');
    try {
      await curriculumApi.generateCurriculum(courseId);
      setCurriculumMessage('Curriculum generated successfully!');
      setHasCurriculum(true);
      const curr = await curriculumApi.getCurriculum(courseId);
      if (curr?.topics) {
        setLiveTopics(
          curr.topics.map((t, idx) => ({
            id: t.id || `topic-${idx}`,
            name: t.title,
            percentage: 0,
            status: 'Developing',
            variant: 'developing',
            isStudyNext: idx === 0,
          }))
        );
      }
    } catch (err) {
      setCurriculumMessage(err.message || 'Failed to generate curriculum. Ensure course materials are uploaded.');
    } finally {
      setIsGeneratingCurriculum(false);
      setTimeout(() => setCurriculumMessage(null), 4000);
    }
  };

  // Construct truthful courseData from real backend attributes
  const courseData = {
    courseName: courseName || 'Course Overview',
    topics: liveTopics,
    mastery: liveOverview ? Math.round(liveOverview.overall_mastery * 100) : 0,
    studyNext: liveStudyNext || {
      topic: 'No Active Recommendation',
      headline: 'Upload materials and complete a study session to unlock recommendations.',
      readiness: 'Developing',
      actionText: 'View Materials',
      reason: 'No prerequisite mastery traced yet.',
      estimatedMinutes: 5,
    },
    learningMap: {
      nodes: liveTopics.map((t) => ({
        id: t.id,
        title: t.name,
        status: t.variant,
        note: t.status,
      })),
      footnote: 'Visualizing curriculum topics in prerequisite progression.',
    },
    recentActivity: [],
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
                  {curriculumMessage && (
                    <p className="text-xs text-[#34d399] font-medium pt-1 animate-pulse">
                      {curriculumMessage}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    disabled={isGeneratingCurriculum}
                    onClick={handleTriggerGenerateCurriculum}
                    className="px-4 py-2 rounded-lg bg-[#a78bfa] text-black font-semibold text-xs hover:bg-[#c4b5fd] transition-colors disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                  >
                    <span className="material-symbols-outlined text-sm">
                      {isGeneratingCurriculum ? 'sync' : 'auto_awesome'}
                    </span>
                    <span>{isGeneratingCurriculum ? 'Generating...' : 'Generate Curriculum'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveSection('materials')}
                    className="px-3 py-2 rounded-lg bg-[#27272a] text-white font-medium text-xs hover:bg-[#3f3f46] transition-colors cursor-pointer"
                  >
                    View Materials
                  </button>
                </div>
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
          weakestTopic={
            liveOverview?.weakest_topic
              ? {
                  name: liveOverview.weakest_topic.title || liveOverview.weakest_topic.name,
                  mastery: Math.round(liveOverview.weakest_topic.mastery * 100),
                }
              : null
          }
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
