import React from 'react';

/**
 * RecentPractice
 * Displays recent practice assessments with scores and dates.
 * Zero gamification (no XP, badges, streaks, or BKT metrics).
 */
export default function RecentPractice({
  sessions = [],
  onViewAllSessions,
}) {
  const getScoreBadgeStyle = (variant) => {
    switch (variant) {
      case 'strong':
        return 'bg-[#065f46]/30 text-[#34d399] border-[#065f46]';
      case 'developing':
        return 'bg-[#27272a] text-[#fafafa] border-[#27272a]';
      case 'attention':
        return 'bg-[#1e1e22] text-amber-300 border-[#27272a]';
      default:
        return 'bg-[#18181b] text-[#a1a1aa] border-[#27272a]';
    }
  };

  return (
    <section className="flex flex-col gap-4 pt-2">
      <div className="flex items-center justify-between">
        <h4 className="text-lg font-medium text-[#a1a1aa]">
          Recent practice
        </h4>
        <button
          type="button"
          onClick={onViewAllSessions}
          className="text-xs font-mono text-[#71717a] hover:text-[#a78bfa] transition-colors cursor-pointer"
        >
          View all sessions &rarr;
        </button>
      </div>

      <div className="border border-[#27272a] rounded-xl divide-y divide-[#27272a] bg-[#121215] overflow-hidden">
        {sessions.map((sess) => (
          <div
            key={sess.id}
            className="p-4 px-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-[#18181b] transition-colors"
          >
            <div className="flex items-center gap-3">
              <span
                className={`material-symbols-outlined text-[20px] ${sess.iconColor}`}
              >
                {sess.icon}
              </span>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-[#fafafa]">
                  {sess.title}
                </span>
                <span className="text-xs text-[#a1a1aa]">
                  {sess.subtitle}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-4 sm:justify-end text-xs font-mono">
              <span
                className={`px-2.5 py-1 rounded border font-semibold ${getScoreBadgeStyle(
                  sess.variant
                )}`}
              >
                {sess.score}
              </span>
              <span className="text-[#71717a]">{sess.time}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

