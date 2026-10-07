import React from 'react';

/**
 * TopicMasteryRow
 * Individual topic row showing topic title, unclipped status badge,
 * percentage, progress bar, and practice link.
 */
export default function TopicMasteryRow({ topic, onPractice }) {
  const { name, mastery = 0, status, variant } = topic;

  const getVariantStyles = () => {
    switch (variant) {
      case 'strong':
        return {
          badge: 'bg-[#065f46]/30 text-[#34d399] border-[#065f46]',
          bar: 'bg-[#34d399]',
          text: 'text-[#34d399]',
        };
      case 'attention':
        return {
          badge: 'bg-[#fbbf24]/10 text-amber-400 border-amber-400/20',
          bar: 'bg-amber-400',
          text: 'text-amber-400',
        };
      case 'developing':
      default:
        return {
          badge: 'bg-[#a78bfa]/10 text-[#a78bfa] border-[#a78bfa]/25',
          bar: 'bg-[#a78bfa]',
          text: 'text-white',
        };
    }
  };

  const { badge, bar, text } = getVariantStyles();

  return (
    <div
      onClick={() => onPractice?.(topic)}
      className="py-3.5 group hover:bg-[#18181c] px-3 -mx-3 rounded-lg transition-colors flex flex-col gap-2 cursor-pointer"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        {/* Left: Topic Name & Badge */}
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-[15px] sm:text-base font-medium text-white group-hover:text-[#a78bfa] transition-colors truncate">
            {name}
          </span>
          <span
            className={`whitespace-nowrap px-2.5 py-0.5 rounded-full text-[11px] font-medium border shrink-0 ${badge}`}
          >
            {status}
          </span>
        </div>

        {/* Right: Percentage & Action Link */}
        <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
          <span className={`text-sm font-semibold font-mono ${text}`}>
            {mastery}%
          </span>
          <span className="text-xs text-[#a1a1aa] group-hover:text-[#a78bfa] transition-colors flex items-center gap-0.5">
            <span>Practice topic</span>
            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-[#1e1e22] h-1.5 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${bar}`}
          style={{ width: `${mastery}%` }}
        />
      </div>
    </div>
  );
}

