import React, { useState, useEffect } from 'react';
import AdaptivePracticeCard from '../components/practice/AdaptivePracticeCard';
import QuickPracticeCard from '../components/practice/QuickPracticeCard';
import MockTestCard from '../components/practice/MockTestCard';
import CustomizePractice from '../components/practice/CustomizePractice';
import CustomizePracticeModal from '../components/practice/CustomizePracticeModal';
import RecentPractice from '../components/practice/RecentPractice';
import PracticeSessionModal from '../components/practice/PracticeSessionModal';
import practiceApi from '../api/practiceApi';
import { defaultPracticeData } from '../data/mockPracticeData';

/**
 * CoursePracticePage
 * Edvora Course Practice Workspace page.
 * Houses Adaptive Practice hero, Quick Practice, Mock Test, Customization, and Recent Practice history.
 */
export default function CoursePracticePage({
  courseId,
  courseName = 'Data Structures & Algorithms',
}) {
  const [practiceData, setPracticeData] = useState(defaultPracticeData);
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
    showToast(`Launching ${mode} practice session...`);

    if (courseId) {
      try {
        const session = await practiceApi.generatePractice(courseId, {
          mode: mode === 'mock-test' ? 'mock_test' : mode,
          num_questions: mode === 'quick' ? 3 : mode === 'mock-test' ? 10 : 5,
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
          return;
        }
      } catch (err) {
        console.warn('Practice generation backend call, using responsive fallback:', err);
      }
    }

    // Fallback simulation if no concepts are indexed yet or offline
    if (mode === 'adaptive') {
      setActiveSession({
        title: `Adaptive Practice: ${practiceData.adaptivePractice.headline}`,
        topic: practiceData.adaptivePractice.topic,
        questionCount: practiceData.adaptivePractice.questionCount,
        estimatedMinutes: practiceData.adaptivePractice.estimatedMinutes,
        difficulty: 'Adaptive (Calibrated)',
        type: 'Targeted Conceptual & Trace',
      });
    } else if (mode === 'quick') {
      setActiveSession({
        title: 'Quick Practice: Mixed Topics',
        topic: 'Arrays, Linked Lists & Trees',
        questionCount: practiceData.quickPractice.questionCount,
        estimatedMinutes: practiceData.quickPractice.estimatedMinutes,
        difficulty: 'Standard',
        type: 'Mixed Rapid Questions',
      });
    } else if (mode === 'mock-test') {
      setActiveSession({
        title: `Comprehensive Mock Test: ${courseName}`,
        topic: 'Full Course Syllabus',
        questionCount: 15,
        estimatedMinutes: 25,
        difficulty: 'Exam Level',
        type: 'Timed Multi-format',
      });
    }
  };

  const handleStartCustomPractice = async (config) => {
    setIsCustomizeOpen(false);
    showToast('Configuring custom practice...');

    if (courseId) {
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
          return;
        }
      } catch (err) {
        console.warn('Custom practice generation fallback:', err);
      }
    }

    setActiveSession({
      title: `Custom Practice: ${config.topic.toUpperCase()}`,
      topic: config.topic === 'all' ? 'All Course Topics' : config.topic,
      questionCount: config.count,
      estimatedMinutes: Math.round(config.count * 1.6),
      difficulty: config.difficulty,
      type: `${config.type.toUpperCase()} Format`,
    });
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
        history={practiceData.recentHistory}
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
