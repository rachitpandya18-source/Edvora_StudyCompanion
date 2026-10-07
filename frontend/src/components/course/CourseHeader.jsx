import React from 'react';

/**
 * CourseHeader
 * Standard course workspace header displaying course name, back link,
 * overall course mastery progress, and optional weakest topic badge.
 */
export default function CourseHeader({
  courseName = 'Data Structures & Algorithms',
  mastery = 68,
  weakestTopic = null,
  onBack,
}) {
  return (
    <div>
      {/* Top Breadcrumb / Return Path */}
      <div className="flex items-center justify-between mb-4">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 text-[14px] font-medium text-[#a1a1aa] hover:text-white transition-colors group cursor-pointer bg-transparent border-0 p-0"
        >
          <span className="material-symbols-outlined text-[18px] group-hover:-translate-x-0.5 transition-transform">
            arrow_back
          </span>
          <span>Back to Dashboard</span>
        </button>
      </div>

      {/* Course Header (Primary Identity & Progress) */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 pt-2">
        <div>
          {/* Course Name only (no code/credits/professor) */}
          <h1 className="text-4xl sm:text-[44px] font-bold tracking-tight text-white leading-tight">
            {courseName}
          </h1>

          {/* Simple Course Mastery Bar (when no badge box) */}
          {!weakestTopic && (
            <div className="flex items-center gap-4 mt-3">
              <span className="text-[16px] text-[#a1a1aa]">Course mastery</span>
              <div className="flex items-center gap-3">
                <div className="w-36 h-2 rounded-full bg-[#18181c] border border-[#2e2e36] overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[#a78bfa] to-[#818cf8] rounded-full transition-all duration-300"
                    style={{ width: `${mastery}%` }}
                  />
                </div>
                <span className="font-mono text-base font-semibold text-white">
                  {mastery}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Optional Right-aligned Mastery + Weakest Topic Stats Badge */}
        {weakestTopic && (
          <div className="flex items-center gap-4 p-3 px-4 rounded-xl bg-[#121215] border border-[#27272a] shrink-0">
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-xs gap-3">
                <span className="text-[#a1a1aa] font-medium">Course mastery</span>
                <span className="font-mono font-bold text-[#a78bfa]">{mastery}%</span>
              </div>
              <div className="w-36 bg-[#18181c] h-1.5 rounded-full overflow-hidden border border-[#27272a]">
                <div
                  className="bg-[#a78bfa] h-full rounded-full transition-all duration-300"
                  style={{ width: `${mastery}%` }}
                />
              </div>
            </div>

            <div className="h-8 w-px bg-[#27272a]" />

            <div className="text-xs text-[#a1a1aa] flex flex-col">
              <span className="text-[11px] uppercase tracking-wider text-[#71717a]">
                Weakest topic
              </span>
              <span className="font-medium text-white flex items-center gap-1">
                {weakestTopic.name}
                <span className="text-amber-400 font-mono font-semibold">
                  · {weakestTopic.mastery}%
                </span>
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
