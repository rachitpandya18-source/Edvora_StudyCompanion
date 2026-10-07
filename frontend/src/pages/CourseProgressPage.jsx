import React, { useState } from 'react';
import CourseMasteryCard from '../components/progress/CourseMasteryCard';
import TopicMastery from '../components/progress/TopicMastery';
import NeedsAttentionCard from '../components/progress/NeedsAttentionCard';
import RecentProgress from '../components/progress/RecentProgress';
import { defaultProgressData } from '../data/mockProgressData';

/**
 * CourseProgressPage
 * Edvora Course Progress Workspace.
 * Comprehensive learning analytics, topic-level mastery distribution,
 * high-priority recommendations, and recent learning events.
 */
export default function CourseProgressPage({
  _courseName = 'Data Structures & Algorithms',
  onNavigateToPractice,
  onNavigateToTutor,
}) {
  const [progressData] = useState(defaultProgressData);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handlePracticeTopic = (topic) => {
    if (onNavigateToPractice) {
      onNavigateToPractice(topic);
    } else {
      showToast(`Opening practice session for ${topic.name}...`);
    }
  };

  const handleStartAdaptivePractice = () => {
    if (onNavigateToPractice) {
      onNavigateToPractice({ name: progressData.needsAttention.topic });
    } else {
      showToast(`Starting adaptive practice for ${progressData.needsAttention.topic}...`);
    }
  };

  const handleAskTutor = () => {
    if (onNavigateToTutor) {
      onNavigateToTutor(progressData.needsAttention.topic);
    } else {
      showToast(`Opening Tutor session on ${progressData.needsAttention.topic}...`);
    }
  };

  const { topicSummary } = progressData;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#18181b] border border-[#a78bfa]/40 text-white text-xs px-4 py-2.5 rounded-lg shadow-xl flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#34d399]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Page Headline & High-Level Breakdown Pill */}
      <section className="space-y-3">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
              Progress
            </h2>
            <p className="text-sm md:text-base text-[#a1a1aa] mt-1.5">
              Your learning progress across this course.
            </p>
          </div>

          {/* Course Coverage Pill Summary */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#121215] border border-[#27272a] text-xs text-[#a1a1aa] self-start md:self-auto shadow-sm">
            <span className="font-medium text-white">
              {topicSummary.total} Total Topics
            </span>
            <span className="text-[#52525b]">·</span>
            <span className="text-[#34d399] font-medium">
              {topicSummary.strong} Strong
            </span>
            <span className="text-[#52525b]">·</span>
            <span className="text-[#a78bfa] font-medium">
              {topicSummary.developing} Developing
            </span>
            <span className="text-[#52525b]">·</span>
            <span className="text-amber-400 font-medium">
              {topicSummary.needsAttention} Needs attention
            </span>
          </div>
        </div>
      </section>

      {/* Top Section: Course Mastery Hero Card */}
      <CourseMasteryCard masteryData={progressData.courseMastery} />

      {/* Two-Column Core Balanced Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (7 cols): Topic Mastery */}
        <div className="lg:col-span-7">
          <TopicMastery
            topics={progressData.topics}
            onPracticeTopic={handlePracticeTopic}
          />
        </div>

        {/* Right Column (5 cols): Needs Attention & Recent Progress */}
        <div className="lg:col-span-5 space-y-6">
          <NeedsAttentionCard
            data={progressData.needsAttention}
            onStartPractice={handleStartAdaptivePractice}
            onAskTutor={handleAskTutor}
          />

          <RecentProgress events={progressData.recentProgress} />
        </div>
      </div>
    </div>
  );
}

