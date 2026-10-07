import React from 'react';

/**
 * RecentProgress
 * Lightweight list of recent learning improvements, assessments, and diagnostic events.
 */
export default function RecentProgress({ events = [] }) {
  const getChangeStyle = (variant) => {
    switch (variant) {
      case 'attention':
        return 'text-amber-400';
      case 'positive':
      default:
        return 'text-[#34d399] font-mono font-medium';
    }
  };

  return (
    <div className="bg-[#121215] rounded-xl border border-[#27272a] p-6 space-y-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-[#a1a1aa] tracking-wider uppercase font-mono">
          Recent Progress
        </span>
        <span className="text-xs text-[#71717a]">
          Last {events.length} events
        </span>
      </div>

      <div className="space-y-3.5">
        {events.map((event, idx) => (
          <div
            key={event.id || idx}
            className={`flex items-start justify-between gap-3 text-xs ${
              idx > 0 ? 'border-t border-[#27272a]/50 pt-3' : ''
            }`}
          >
            <div className="space-y-0.5">
              <p className="font-medium text-white">{event.title}</p>
              <p className={getChangeStyle(event.changeVariant)}>
                {event.change}
              </p>
            </div>
            <span className="text-[11px] text-[#a1a1aa] font-mono shrink-0">
              {event.time}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

