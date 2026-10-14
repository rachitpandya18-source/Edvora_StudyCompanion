import React, { useState, useEffect } from 'react';
import AdaptivePracticeCard from '../components/practice/AdaptivePracticeCard';
import QuickPracticeCard from '../components/practice/QuickPracticeCard';
import MockTestCard from '../components/practice/MockTestCard';
import CustomizePractice from '../components/practice/CustomizePractice';
import CustomizePracticeModal from '../components/practice/CustomizePracticeModal';
import RecentPractice from '../components/practice/RecentPractice';
import PracticeSessionModal from '../components/practice/PracticeSessionModal';
import practiceApi from '../api/practiceApi';
import curriculumApi from '../api/curriculumApi';

/**
 * CoursePracticePage
 * Edvora Course Practice Workspace page.
 * Houses Adaptive Practice hero, Quick Practice, Mock Test, Customization, and Recent Practice history.
 */
export default function CoursePracticePage({
  courseId,
  courseName = 'Course Overview',
}) {
  const [practiceData, setPracticeData] = useState({
    courseName,
    adaptivePractice: {
      topic: 'Core Curriculum',
      mastery: 0,
      statusText: 'Ready',
      badge: 'RECOMMENDED · ADAPTIVE PRACTICE',
      headline: `Practice ${courseName}`,
      description: 'Strengthen core concepts with calibrated questions.',
      questionCount: 5,
      estimatedMinutes: 8,
      whyThis: 'Edvora adaptive engine prioritizes active learning for this course.',
    },
    quickPractice: {
      title: 'Quick Practice',
      description: 'Practice for a few minutes across recent topics without configuring settings.',
      questionCount: 5,
      estimatedMinutes: 5,
      metadata: '~5 minutes · 5 mixed questions',
    },
    mockTest: {
      title: 'Mock Test',
      description: 'Simulate a timed exam across all covered topics in this course.',
      metadata: 'Timed · Comprehensive · Exam conditions',
    },
    recentSessions: [],
  });
  const [courseTopics, setCourseTopics] = useState([]);
  const [isCustomizeOpen, setIsCustomizeOpen] = useState(false);
  const [activeSession, setActiveSession] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const loadRecentSessions = (cId) => {
    if (!cId) return;
    practiceApi.getRecentAttempts(cId, 5)
      .then((attempts) => {
        if (Array.isArray(attempts)) {
          const mapped = attempts.map((att) => {
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
            const variant = pct >= 80 ? 'strong' : pct >= 50 ? 'developing' : 'attention';
            const icon = pct >= 80 ? 'check_circle' : pct >= 50 ? 'bolt' : 'school';
            const iconColor = pct >= 80 ? 'text-[#34d399]' : pct >= 50 ? 'text-[#a78bfa]' : 'text-amber-300';
            const dateStr = att.submitted_at || att.created_at;
            const time = dateStr ? new Date(dateStr).toLocaleDateString() : 'Recent';

            return {
              id: att.id,
              rawAttempt: att,
              title: att.assessment_title || 'Practice Assessment',
              subtitle: `${att.answers?.length || 0} questions evaluated`,
              variant,
              icon,
              iconColor,
              score: `${pct}%`,
              time,
            };
          });
          setPracticeData((prev) => ({
            ...prev,
            recentSessions: mapped,
          }));
        }
      })
      .catch((err) => {
        console.warn('Failed to load recent practice sessions:', err);
      });
  };

  useEffect(() => {
    if (!courseId) return;
    loadRecentSessions(courseId);

    practiceApi.getPracticeOptions(courseId)
      .then((opts) => {
        if (opts && Array.isArray(opts.topics) && opts.topics.length > 0) {
          setCourseTopics((prev) => (prev.length > 0 ? prev : opts.topics));
        }
        if (opts && opts.recommended_focus_concept) {
          setPracticeData((prev) => ({
            ...prev,
            adaptivePractice: {
              ...prev.adaptivePractice,
              headline: opts.recommended_focus_concept.concept_title,
              topic: opts.recommended_focus_concept.topic_title || 'Core Curriculum',
              reason: opts.recommended_focus_concept.reason,
            },
          }));
        }
      })
      .catch(() => {});

    curriculumApi.getCurriculum(courseId)
      .then((curr) => {
        if (curr?.topics && Array.isArray(curr.topics) && curr.topics.length > 0) {
          setCourseTopics(curr.topics);
        }
      })
      .catch(() => {});
  }, [courseId]);

  const handleStartPractice = async (mode) => {
    if (!courseId) {
      showToast('Please select a course to practice.');
      return;
    }
    showToast(`Launching ${mode} practice session...`);

    try {
      const session = await practiceApi.generatePractice(courseId, {
        mode: mode === 'mock-test' ? 'mock_test' : mode,
        question_count: mode === 'quick' ? 3 : mode === 'mock-test' ? 10 : 3,
      });

      if (session && session.questions && session.questions.length > 0) {
        setActiveSession({
          courseId,
          assessmentId: session.assessment_id,
          attemptId: session.attempt_id,
          title:
            mode === 'adaptive'
              ? `Adaptive Practice: ${session.questions[0].concept_title || 'Targeted'}`
              : mode === 'quick'
              ? 'Quick Practice: Mixed Topics'
              : `Comprehensive Mock Test: ${courseName}`,
          topic: session.questions[0].concept_title || 'Course Concepts',
          questionCount: session.questions.length,
          questions: session.questions,
          estimatedMinutes: Math.round(session.questions.length * 1.8),
          difficulty: mode === 'adaptive' ? 'Adaptive (Calibrated)' : 'Standard',
          type: 'Concept Evaluation',
        });
      } else {
        showToast('No practice questions available for this course yet. Please index curriculum materials first.');
      }
    } catch (err) {
      console.warn('Practice generation backend call failed:', err);
      showToast(err?.data?.detail || err?.message || 'Unable to generate practice session. Ensure course curriculum is indexed.');
    }
  };

  const handleStartCustomPractice = async (config) => {
    if (!courseId) {
      showToast('Please select a course to practice.');
      return;
    }
    showToast('Configuring custom practice...');

    const diffMap = {
      adaptive: 'medium',
      foundational: 'easy',
      standard: 'medium',
      challenging: 'hard',
    };
    const mappedDifficulty = diffMap[config.difficulty] || 'medium';
    const questionTypes = config.type && config.type !== 'mixed' ? [config.type] : undefined;
    const topicId = config.topic && config.topic !== 'all' ? config.topic : undefined;
    const count = Number(config.count) || 5;

    // Resolve human-readable topic title
    const selectedTopicObj = courseTopics.find((t) => t.id === config.topic);
    const displayTopicTitle = selectedTopicObj ? selectedTopicObj.title : (config.topic === 'all' ? 'All Course Topics' : config.topic);

    try {
      const session = await practiceApi.generatePractice(courseId, {
        mode: 'adaptive',
        topic_id: topicId,
        question_count: count,
        question_types: questionTypes,
        difficulty: mappedDifficulty,
      });

      if (session && session.questions && session.questions.length > 0) {
        setIsCustomizeOpen(false);
        setActiveSession({
          courseId,
          assessmentId: session.assessment_id,
          attemptId: session.attempt_id,
          title: `Custom Practice: ${displayTopicTitle}`,
          topic: displayTopicTitle,
          questionCount: session.questions.length,
          questions: session.questions,
          estimatedMinutes: Math.round(session.questions.length * 1.6),
          difficulty: config.difficulty === 'adaptive' ? 'Adaptive (Calibrated)' : config.difficulty.charAt(0).toUpperCase() + config.difficulty.slice(1),
          type: config.type === 'mixed' ? 'Mixed Types' : `${config.type.replace('_', ' ').toUpperCase()} Format`,
        });
      } else {
        const errorMsg = 'No custom practice questions could be generated for the selected topic.';
        showToast(errorMsg);
        throw new Error(errorMsg);
      }
    } catch (err) {
      console.warn('Custom practice generation error:', err);
      const detail = err?.data?.detail || err?.response?.data?.detail || err?.message || 'Unable to generate custom practice session.';
      showToast(detail);
      throw err;
    }
  };

  return (
    <div className="space-y-10">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-lg bg-[#18181b] border border-[#a78bfa]/50 text-xs font-mono text-white shadow-xl animate-in fade-in slide-in-from-bottom duration-200">
          {toastMessage}
        </div>
      )}

      {/* Practice Page Header */}
      <div className="flex flex-col gap-1">
        <h2 className="text-3xl font-bold tracking-tight text-white">
          Practice
        </h2>
        <p className="text-base text-[#a1a1aa]">
          Strengthen what you know. Practice what needs work.
        </p>
      </div>

      {/* 1. Primary Experience: Adaptive Practice Hero */}
      <AdaptivePracticeCard
        adaptiveData={practiceData.adaptivePractice}
        onStartPractice={handleStartPractice}
      />

      {/* 2. Secondary Experiences Grid: Quick Practice & Mock Test */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <QuickPracticeCard
          quickData={practiceData.quickPractice}
          onStartPractice={handleStartPractice}
        />
        <MockTestCard
          courseName={courseName}
          mockData={practiceData.mockTest}
          onStartPractice={handleStartPractice}
        />
      </section>

      {/* 3. Custom Practice CTA Strip */}
      <CustomizePractice
        onOpenCustomize={() => setIsCustomizeOpen(true)}
        onOpenModal={() => setIsCustomizeOpen(true)}
      />

      {/* 4. Recent Practice History */}
      <RecentPractice
        sessions={practiceData.recentSessions || []}
        onReviewSession={(session) => {
          if (session?.rawAttempt?.answers && session.rawAttempt.answers.length > 0) {
            const initialAns = {};
            session.rawAttempt.answers.forEach((a) => {
              if (a.student_answer) initialAns[a.question_id] = a.student_answer;
            });
            setActiveSession({
              courseId,
              assessmentId: session.rawAttempt.assessment_id,
              attemptId: session.rawAttempt.id,
              title: `Review: ${session.title}`,
              topic: session.title,
              questionCount: session.rawAttempt.answers.length,
              questions: session.rawAttempt.answers.map((a) => ({
                id: a.question_id,
                prompt: a.question_prompt || 'Practice Question',
                type: a.question_type || 'Multiple Choice',
                options: (a.options_json || [a.student_answer, a.correct_answer].filter(Boolean)).map((opt) =>
                  typeof opt === 'string' ? { id: opt, text: opt } : opt
                ),
                concept_title: a.concept_title || a.concept_name,
                concept_name: a.concept_name,
                explanation: a.explanation,
              })),
              initialEvaluation: session.rawAttempt,
              initialAnswers: initialAns,
            });
          } else {
            showToast(`Opening review for ${session.title}...`);
          }
        }}
      />

      {/* Custom Practice Modal */}
      {isCustomizeOpen && (
        <CustomizePracticeModal
          isOpen={isCustomizeOpen}
          onClose={() => setIsCustomizeOpen(false)}
          onStartCustomPractice={handleStartCustomPractice}
          topics={courseTopics}
        />
      )}

      {/* Active Practice Session Modal */}
      {activeSession && (
        <PracticeSessionModal
          isOpen={Boolean(activeSession)}
          sessionConfig={activeSession}
          onClose={() => setActiveSession(null)}
          onAttemptCompleted={(result) => {
            const rawScore = result.score ?? 0;
            const maxScore = result.max_score ?? 1;
            const pct = Math.min(
              100,
              Math.max(
                0,
                result.percentage !== undefined && result.percentage !== null
                  ? Math.round(result.percentage)
                  : Math.round((rawScore / (maxScore || 1)) * 100)
              )
            );
            showToast(`Assessment submitted! Score: ${pct}% (${rawScore}/${maxScore})`);
            loadRecentSessions(courseId);
          }}
        />
      )}
    </div>
  );
}
