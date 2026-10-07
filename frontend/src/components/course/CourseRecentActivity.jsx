import React from 'react';

/**
 * CourseRecentActivity
 * Shows recent learning events inside the course in chronological order.
 */
export default function CourseRecentActivity({ activities = [] }) {
  const getIconContainerStyle = (variant) => {
    switch (variant) {
      case 'strong':
      case 'success':
        return 'bg-[#34d399]/10 border-[#34d399]/20 text-[#34d399]';
      case 'accent':
      case 'tutor':
        return 'bg-[#a78bfa]/10 border-[#a78bfa]/20 text-[#a78bfa]';
      default:
        return 'bg-[#222227] border-[#2e2e36] text-[#a1a1aa]';
    }
  };

  const getDetailStyle = (variant) => {
    switch (variant) {
      case 'strong':
      case 'success':
        return 'text-[#34d399]';
      case 'accent':
      case 'tutor':
        return 'text-[#a78bfa]';
      default:
        return 'text-[#71717a]';
    }
  };

  return (
    <section className="lg:col-span-5 rounded-xl border border-[#222227] bg-[#121215] p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-[#222227] pb-4">
        <div>
          <h3 className="text-xl sm:text-[22px] font-bold text-white tracking-tight">
            Recent activity
          </h3>
          <p className="text-[14px] text-[#a1a1aa] mt-0.5">
            Your learning history in this course
          </p>
        </div>
        <span className="text-xs font-mono text-[#71717a]">Chronological</span>
      </div>

      {/* Activity List */}
      <div className="space-y-3">
        {activities.map((item) => (
          <div
            key={item.id}
            className="p-3.5 rounded-lg bg-[#18181c] border border-[#222227] flex items-start gap-3.5"
          >
            <div
              className={`w-7 h-7 rounded-md border flex items-center justify-center shrink-0 mt-0.5 ${getIconContainerStyle(
                item.variant
              )}`}
            >
              <span className="material-symbols-outlined text-[16px]">
                {item.icon}
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-medium text-white leading-snug">
                {item.title}
              </p>
              <div className="flex items-center gap-2 mt-1 text-[13px] font-mono text-[#a1a1aa]">
                <span>{item.time}</span>
                <span>•</span>
                <span className={getDetailStyle(item.variant)}>{item.detail}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

