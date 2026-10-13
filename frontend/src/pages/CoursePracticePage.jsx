import React, { useState, useEffect } from 'react';
import AdaptivePracticeCard from '../components/practice/AdaptivePracticeCard';
import QuickPracticeCard from '../components/practice/QuickPracticeCard';
import MockTestCard from '../components/practice/MockTestCard';
import CustomizePractice from '../components/practice/CustomizePractice';
import CustomizePracticeModal from '../components/practice/CustomizePracticeModal';
import RecentPractice from '../components/practice/RecentPractice';
import PracticeSessionModal from '../components/practice/PracticeSessionModal';
import practiceApi from '../api/practiceApi';

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
  const [isCustomizeOpen, setIsCustomizeOpen] = useState(false);
  const [activeSession, setActiveSession] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  useEffect(() => {
    if (!courseId) return;
    practiceApi.getPracticeOptions(courseId)
      .then((opts) => {
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
      showToast(err?.response?.data?.detail || 'Unable to generate practice session. Ensure course curriculum is indexed.');
    }
  };

  const handleStartCustomPractice = async (config) => {
    setIsCustomizeOpen(false);
    if (!courseId) {
      showToast('Please select a course to practice.');
      return;
    }
    showToast('Configuring custom practice...');

    try {
      const session = await practiceApi.generatePractice(courseId, {
        mode: 'adaptive',
        topic_id: config.topic !== 'all' ? config.topic : undefined,
        num_questions: config.count || 5,
        difficulty: config.difficulty,
      });

      if (session && session.questions && session.questions.length > 0) {
        setActiveSession({
          courseId,
          assessmentId: session.assessment_id,
          attemptId: session.attempt_id,
          title: `Custom Practice: ${config.topic.toUpperCase()}`,
          topic: config.topic === 'all' ? 'All Course Topics' : config.topic,
          questionCount: session.questions.length,
          questions: session.questions,
          estimatedMinutes: Math.round(session.questions.length * 1.6),
          difficulty: config.difficulty,
          type: `${config.type.toUpperCase()} Format`,
        });
      } else {
        showToast('No custom practice questions could be generated for the selected topic.');
      }
    } catch (err) {
      console.warn('Custom practice generation error:', err);
      showToast(err?.response?.data?.detail || 'Unable to generate custom practice session.');
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
          mockData={practiceData.mockTest}
          onStartPractice={handleStartPractice}
        />
      </section>

      {/* 3. Custom Practice CTA Strip */}
      <CustomizePractice onOpenModal={() => setIsCustomizeOpen(true)} />

      {/* 4. Recent Practice History */}
      <RecentPractice
        sessions={practiceData.recentSessions || []}
        onReviewSession={(session) => {
          showToast(`Opening review for ${session.title}...`);
        }}
      />

      {/* Custom Practice Modal */}
      {isCustomizeOpen && (
        <CustomizePracticeModal
          isOpen={isCustomizeOpen}
          onClose={() => setIsCustomizeOpen(false)}
          onStartCustomPractice={handleStartCustomPractice}
        />
      )}

      {/* Active Practice Session Modal */}
      {activeSession && (
        <PracticeSessionModal
          isOpen={Boolean(activeSession)}
          sessionConfig={activeSession}
          onClose={() => setActiveSession(null)}
          onAttemptCompleted={(result) => {
            showToast(`Assessment submitted! Score: ${Math.round((result.score ?? 1) * 100)}%`);
          }}
        />
      )}
    </div>
  );
}
