import React, { useState, useEffect } from 'react';
import CourseMasteryCard from '../components/progress/CourseMasteryCard';
import TopicMastery from '../components/progress/TopicMastery';
import NeedsAttentionCard from '../components/progress/NeedsAttentionCard';
import RecentProgress from '../components/progress/RecentProgress';
import analyticsApi from '../api/analyticsApi';

/**
 * CourseProgressPage
 * Edvora Course Progress Workspace.
 * Comprehensive learning analytics, topic-level mastery distribution,
 * high-priority recommendations, and recent learning events.
 */
export default function CourseProgressPage({
  courseId,
  courseName = 'Course Overview',
  onNavigateToPractice,
  onNavigateToTutor,
}) {
  const [progressData, setProgressData] = useState(() => ({
    courseName,
    courseMastery: {
      percentage: 0,
      status: 'Developing',
      statusVariant: 'developing',
      message: 'Complete practice questions and engage with the course tutor to begin tracking mastery.',
    },
    topicSummary: {
      total: 0,
      strong: 0,
      developing: 0,
      needsAttention: 0,
    },
    topics: [],
    needsAttention: {
      topic: 'Core Course Concepts',
      mastery: 0,
      status: 'Needs attention',
      description: 'Review course curriculum and start adaptive practice to trace concept mastery.',
      recommendedNextStep: 'Start adaptive practice session',
      footnote: 'Mastery dynamically traced via Bayesian Knowledge Tracing (BKT).',
      practiceActionLabel: 'Start adaptive practice',
      tutorActionLabel: 'Ask Tutor for help →',
    },
    recentEvents: [],
  }));
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  useEffect(() => {
    if (!courseId) return;

    analyticsApi.getOverview(courseId)
      .then((ov) => {
        if (ov) {
          setProgressData((prev) => {
            const mappedTopics = (ov.topic_summaries || []).map((t, idx) => ({
              id: t.topic_id || `t-${idx}`,
              name: t.title,
              mastery: Math.round(t.average_mastery * 100),
              statusVariant:
                t.status === 'mastered' ? 'strong' : t.status === 'proficient' ? 'developing' : 'attention',
              statusText: t.status.charAt(0).toUpperCase() + t.status.slice(1),
              masteredCount: t.mastered_concepts,
              totalCount: t.total_concepts,
              icon: 'school',
            }));

            // Find lowest mastery topic for needsAttention
            const lowestTopic = mappedTopics.length > 0
              ? [...mappedTopics].sort((a, b) => a.mastery - b.mastery)[0]
              : null;

            return {
              ...prev,
              courseMastery: {
                ...prev.courseMastery,
                percentage: Math.round(ov.overall_mastery * 100),
                overallMastery: Math.round(ov.overall_mastery * 100),
                syllabusCompletion: Math.round(ov.syllabus_completion_rate * 100),
                readinessScore: Math.round(ov.readiness_score),
              },
              topics: mappedTopics,
              topicSummary: {
                total: ov.topic_summaries?.length || 0,
                strong: ov.mastery_distribution?.mastered || 0,
                developing: ov.mastery_distribution?.developing || 0,
                needsAttention: ov.mastery_distribution?.struggling || 0,
              },
              needsAttention: lowestTopic
                ? {
                    topic: lowestTopic.name,
                    mastery: lowestTopic.mastery,
                    status: 'Needs attention',
                    description: `Topic mastery is currently ${lowestTopic.mastery}%. Reinforce fundamentals with adaptive practice.`,
                    recommendedNextStep: `Review ${lowestTopic.name} → Practice targeted questions`,
                    footnote: 'Based on your Bayesian Knowledge Tracing mastery model.',
                    practiceActionLabel: 'Start adaptive practice',
                    tutorActionLabel: `Ask Tutor about ${lowestTopic.name} →`,
                  }
                : prev.needsAttention,
            };
          });
        }
      })
      .catch(() => {});
  }, [courseId]);

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
              Your learning progress across {courseName}.
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
        {/* Left Column (Span 7): Topic Breakdown List */}
        <div className="lg:col-span-7">
          <TopicMastery
            topics={progressData.topics}
            onPracticeTopic={handlePracticeTopic}
          />
        </div>

        {/* Right Column (Span 5): High Priority Attention & Chronological History */}
        <div className="lg:col-span-5 space-y-6">
          <NeedsAttentionCard
            needsAttentionData={progressData.needsAttention}
            onStartPractice={handleStartAdaptivePractice}
            onAskTutor={handleAskTutor}
          />
          <RecentProgress events={progressData.recentEvents || []} />
        </div>
      </div>
    </div>
  );
}
