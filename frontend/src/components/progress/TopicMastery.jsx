import React from 'react';
import TopicMasteryRow from './TopicMasteryRow';

/**
 * TopicMastery
 * Container card for topic-level mastery list.
 */
export default function TopicMastery({ topics = [], onPracticeTopic }) {
  return (
    <section className="bg-[#121215] rounded-xl border border-[#27272a] p-6 space-y-4 shadow-sm">
      <div className="border-b border-[#27272a]/60 pb-3">
        <h3 className="text-base font-bold text-white tracking-tight">Topic Mastery</h3>
        <p className="text-xs text-[#a1a1aa] mt-0.5">Topic-level mastery across core curriculum modules.</p>
      </div>

      <div className="divide-y divide-[#27272a]/50">
        {topics.map((topic) => (
          <TopicMasteryRow
            key={topic.id}
            topic={topic}
            onPractice={onPracticeTopic}
          />
        ))}
      </div>
    </section>
  );
}

