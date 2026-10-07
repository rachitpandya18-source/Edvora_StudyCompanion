import React from 'react';

/**
 * CourseMasteryCard
 * Prominent card summarizing overall course curriculum mastery,
 * status badge, progress bar, and data-driven guidance message.
 */
export default function CourseMasteryCard({ masteryData }) {
  const {
    percentage = 68,
    status = 'Developing',
    statusVariant = 'developing',
    message = "You're making steady progress. AVL Trees needs the most attention.",
  } = masteryData || {};

  const getStatusStyles = () => {
    switch (statusVariant) {
      case 'strong':
        return {
          badge: 'bg-[#065f46]/30 text-[#34d399] border-[#065f46]',
          bar: 'bg-[#34d399]',
        };
      case 'attention':
        return {
          badge: 'bg-[#fbbf24]/10 text-[#fbbf24] border-[#fbbf24]/30',
          bar: 'bg-[#fbbf24]',
        };
      case 'developing':
      default:
        return {
          badge: 'bg-[#a78bfa]/10 text-[#a78bfa] border-[#a78bfa]/25',
          bar: 'bg-[#a78bfa]',
        };
    }
  };

  const { badge, bar } = getStatusStyles();

  return (
    <section className="bg-[#121215] rounded-xl border border-[#27272a] p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[11px] font-semibold text-[#a1a1aa] tracking-wider uppercase font-mono">
          Course Mastery
        </span>
        <span
          className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${badge}`}
        >
          {status}
        </span>
      </div>

      <div className="flex items-baseline gap-4 mb-4">
        <span className="text-5xl font-extrabold tracking-tight text-white font-mono">
          {percentage}%
        </span>
        <span className="text-xs text-[#a1a1aa]">
          overall curriculum mastered
        </span>
      </div>

      {/* Horizontal Progress Bar */}
      <div className="w-full bg-[#1e1e22] h-2 rounded-full overflow-hidden mb-3">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${bar}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <p className="text-xs text-[#a1a1aa]">
        {message}
      </p>
    </section>
  );
}

