import React, { useState } from 'react';
import AdaptivePracticeCard from '../components/practice/AdaptivePracticeCard';
import QuickPracticeCard from '../components/practice/QuickPracticeCard';
import MockTestCard from '../components/practice/MockTestCard';
import CustomizePractice from '../components/practice/CustomizePractice';
import CustomizePracticeModal from '../components/practice/CustomizePracticeModal';
import RecentPractice from '../components/practice/RecentPractice';
import PracticeSessionModal from '../components/practice/PracticeSessionModal';
import { defaultPracticeData } from '../data/mockPracticeData';

/**
 * CoursePracticePage
 * Edvora Course Practice Workspace page.
 * Houses Adaptive Practice hero, Quick Practice, Mock Test, Customization, and Recent Practice history.
 */
export default function CoursePracticePage({
  courseName = 'Data Structures & Algorithms',
}) {
  const [practiceData] = useState(defaultPracticeData);
  const [isCustomizeOpen, setIsCustomizeOpen] = useState(false);
  const [activeSession, setActiveSession] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleStartPractice = (mode) => {
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

  const handleStartCustomPractice = (config) => {
    setIsCustomizeOpen(false);
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
          courseName={courseName}
          mockTestData={practiceData.mockTest}
          onStartPractice={handleStartPractice}
        />
      </section>

      {/* 3. Quiet Custom Practice Section */}
      <CustomizePractice onOpenCustomize={() => setIsCustomizeOpen(true)} />

      {/* 4. Compact Recent Practice Section */}
      <RecentPractice
        sessions={practiceData.recentSessions}
        onViewAllSessions={() =>
          showToast('All past assessment sessions are archived under your course history.')
        }
      />

      {/* Customize Practice Modal */}
      <CustomizePracticeModal
        isOpen={isCustomizeOpen}
        onClose={() => setIsCustomizeOpen(false)}
        onStartCustomPractice={handleStartCustomPractice}
      />

      {/* Interactive Practice Session Launch Modal */}
      <PracticeSessionModal
        isOpen={Boolean(activeSession)}
        sessionConfig={activeSession}
        onClose={() => setActiveSession(null)}
      />
    </div>
  );
}

