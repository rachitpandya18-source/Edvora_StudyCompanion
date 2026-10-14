import { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import QuickStartCard from '../components/dashboard/QuickStartCard';
import CourseCard from '../components/dashboard/CourseCard';
import StudyNextCard from '../components/dashboard/StudyNextCard';
import RecentActivity from '../components/dashboard/RecentActivity';
import LearningSnapshot from '../components/dashboard/LearningSnapshot';
import curriculumApi from '../api/curriculumApi';
import analyticsApi from '../api/analyticsApi';
import practiceApi from '../api/practiceApi';
import {
  mockStudentProfile,
} from '../data/mockDashboardData';

export default function DashboardPage({
  user = mockStudentProfile,
  courses = [],
  onNavigate,
  onNavigateToCourse,
  onEnterWorkspace,
  onCreateCourse,
}) {
  const [studyNext, setStudyNext] = useState(null);
  const [courseMasteries, setCourseMasteries] = useState({});
  const [activities, setActivities] = useState([]);
  const [snapshot, setSnapshot] = useState({
    strongCount: 0,
    developingCount: 0,
    attentionCount: 0,
  });
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    if (!courses || courses.length === 0) return;

    const firstCourseId = courses[0].id;

    // Fetch live study-next recommendation from curriculum API
    curriculumApi.getStudyNext(firstCourseId)
      .then((rec) => {
        if (rec) {
          const displayTopic = rec.concept_name || rec.topic_title || rec.concept_title || 'Core Curriculum';
          const displayRationale = rec.rationale || rec.reason || (rec.prerequisite_depth != null
            ? `Prioritized based on prerequisite graph depth (${rec.prerequisite_depth}).`
            : 'Recommended next step for core curricular progression.');
          const masteryPct = Math.round((rec.mastery_probability ?? 0) * 100);
          const actions = rec.recommended_actions?.length
            ? rec.recommended_actions.map((act) => ({
                id: `act-${act.step}`,
                step: String(act.step),
                title: act.title,
                durationOrPage: act.details || (act.action_type === 'practice_quiz' ? '5 questions' : '5 mins'),
              }))
            : [
                {
                  id: 'act-1',
                  step: '1',
                  title: 'Review Conceptual Summary with Course Tutor',
                  durationOrPage: '5 mins',
                },
                {
                  id: 'act-2',
                  step: '2',
                  title: 'Complete Adaptive Calibration Practice',
                  durationOrPage: '5 questions',
                },
              ];

          setStudyNext({
            courseId: firstCourseId,
            courseName: courses[0].title,
            topic: displayTopic,
            mastery: masteryPct,
            status: rec.status_text || 'Recommended',
            rationale: displayRationale,
            recommendedActions: actions,
          });
        }
      })
      .catch(() => {});

    // Fetch overview analytics and mastery for each course
    courses.forEach((c) => {
      analyticsApi.getOverview(c.id)
        .then((ov) => {
          if (ov && typeof ov.overall_mastery === 'number') {
            const masteryPct = Math.round(ov.overall_mastery * 100);
            setCourseMasteries((prev) => ({
              ...prev,
              [c.id]: masteryPct,
            }));
            if (c.id === firstCourseId) {
              setStudyNext((prev) => (prev ? { ...prev, mastery: masteryPct } : prev));
            }
          }
          if (c.id === firstCourseId && ov?.mastery_distribution) {
            setSnapshot({
              strongCount: ov.mastery_distribution.mastered || 0,
              developingCount: ov.mastery_distribution.developing || 0,
              attentionCount: ov.mastery_distribution.struggling || 0,
            });
          }
        })
        .catch(() => {});
    });

    // Fetch real recent attempts for activities feed
    practiceApi.getRecentAttempts(firstCourseId, 4)
      .then((attempts) => {
        if (Array.isArray(attempts) && attempts.length > 0) {
          const act = attempts.map((att) => {
            const rawScore = att.score ?? 0;
            const maxScore = att.max_score ?? att.answers?.length ?? 1;
            const pct = Math.min(
              100,
              Math.max(
                0,
                att.percentage !== undefined && att.percentage !== null
                  ? Math.round(att.percentage)
                  : Math.round((rawScore / (maxScore || 1)) * 100)
              )
            );
            const variant = pct >= 80 ? 'strong' : pct >= 50 ? 'accent' : 'neutral';
            const icon = pct >= 80 ? 'check_circle' : pct >= 50 ? 'bolt' : 'school';
            const dateStr = att.submitted_at || att.created_at;
            const time = dateStr
              ? new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : 'Recent';

            return {
              id: att.id,
              variant,
              icon,
              title: att.assessment_title || 'Adaptive Practice Session',
              course: courses[0]?.title || 'Course',
              detail: `Score: ${pct}% (${att.answers?.length || 0} questions)`,
              time,
            };
          });
          setActivities(act);
        }
      })
      .catch(() => {});
  }, [courses]);

  const rawName = user?.name || user?.full_name || user?.username || 'Student';
  const firstName = rawName.split(' ')[0];

  const showToast = (msg) => {
    setNotification(msg);
    setTimeout(() => {
      setNotification(null);
    }, 3000);
  };

  const primaryCourse = courses && courses.length > 0 ? courses[0] : null;
  const targetCourseId = primaryCourse?.id;
  const targetCourseTitle = primaryCourse?.title || 'Your Course';

  const quickStartActions = [
    {
      id: 'continue',
      category: 'CONTINUE',
      title: 'Continue learning',
      subtitle: `${targetCourseTitle} · Overview`,
      icon: 'play_arrow',
      target: 'workspace',
      courseId: targetCourseId,
      accentColor: 'accent',
    },
    {
      id: 'tutor',
      category: 'ASK TUTOR',
      title: 'Ask your tutor',
      subtitle: `Ask about ${targetCourseTitle}`,
      icon: 'chat_bubble',
      target: 'workspace_tutor',
      courseId: targetCourseId,
      accentColor: 'surface',
    },
    {
      id: 'practice',
      category: 'PRACTICE',
      title: 'Practice weak topics',
      subtitle: `Targeted practice for ${targetCourseTitle}`,
      icon: 'psychology',
      target: 'workspace_practice',
      courseId: targetCourseId,
      accentColor: 'attention',
    },
    {
      id: 'materials',
      category: 'RESOURCES',
      title: 'Browse materials',
      subtitle: `View ${targetCourseTitle} resources`,
      icon: 'description',
      target: 'workspace_materials',
      courseId: targetCourseId,
      accentColor: 'surface',
    },
  ];

  const handleQuickAction = (action) => {
    if (!action.courseId) {
      showToast('Please create or select a course to start.');
      return;
    }
    const targetTab = action.id === 'continue' ? 'overview' : action.id;
    if (onNavigateToCourse) {
      onNavigateToCourse(action.courseId, targetTab);
    } else if (onEnterWorkspace) {
      onEnterWorkspace(action.courseId);
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
    const courseId = item?.courseId || (courses && courses.length > 0 ? courses[0].id : null);
    if (!courseId) {
      showToast('Please create or select a course first.');
      return;
    }
    if (onNavigateToCourse) {
      onNavigateToCourse(courseId, 'practice');
    } else if (onEnterWorkspace) {
      onEnterWorkspace(courseId);
    }
  };

  const handleViewCourse = (item) => {
    const courseId = item?.courseId || (courses && courses.length > 0 ? courses[0].id : null);
    if (!courseId) {
      showToast('Please create or select a course first.');
      return;
    }
    if (onNavigateToCourse) {
      onNavigateToCourse(courseId, 'overview');
    } else if (onEnterWorkspace) {
      onEnterWorkspace(courseId);
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
      if (onNavigate) {
        onNavigate('settings');
      }
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
            {quickStartActions.map((action) => (
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
              {courses.length === 0 ? (
                <div className="p-8 text-center rounded-xl bg-[#121215] border border-[#27272a] space-y-3">
                  <span className="material-symbols-outlined text-3xl text-primary">school</span>
                  <h3 className="text-sm font-semibold text-white">No courses yet</h3>
                  <p className="text-xs text-[#a1a1aa] max-w-sm mx-auto">
                    Create your first course to start studying with personalized AI tutoring and adaptive practice.
                  </p>
                  <button
                    type="button"
                    onClick={onCreateCourse}
                    className="px-4 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold cursor-pointer transition-colors"
                  >
                    Create Your First Course
                  </button>
                </div>
              ) : (
                courses.map((course) => (
                  <CourseCard
                    key={course.id}
                    course={{
                      ...course,
                      mastery: courseMasteries[course.id] ?? course.mastery ?? 0,
                    }}
                    onContinue={handleContinueCourse}
                  />
                ))
              )}
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

