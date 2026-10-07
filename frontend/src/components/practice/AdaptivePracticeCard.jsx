import React, { useState } from 'react';

/**
 * AdaptivePracticeCard
 * Primary hero card for the recommended adaptive practice session.
 * Features an expandable "Why this?" educational rationale.
 */
export default function AdaptivePracticeCard({
  adaptiveData,
  onStartPractice,
}) {
  const [whyThisOpen, setWhyThisOpen] = useState(false);

  const {
    badge = 'RECOMMENDED · ADAPTIVE PRACTICE',
    mastery = 43,
    statusText = 'Needs attention',
    headline = 'Strengthen AVL Trees',
    description = 'Your recent answers suggest difficulty with Left-Right and Right-Left rotations.',
    questionCount = 5,
    estimatedMinutes = 8,
    whyThis = 'Edvora selected AVL Trees because your recent answers in the Tutor and Trees assessment showed difficulty resolving zigzag imbalances before balancing the root.',
  } = adaptiveData || {};

  return (
    <section className="rounded-xl border border-[#27272a] bg-[#121215] p-7 lg:p-9 relative overflow-hidden transition-all duration-200 hover:border-[#3f3f46] shadow-xl">
      {/* Subtle Violet Ambient Depth Accent */}
      <div className="absolute -right-24 -top-24 w-80 h-80 bg-[#a78bfa]/10 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col gap-6 relative z-10">
        {/* Top Badges & Pill */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#a78bfa]/10 border border-[#a78bfa]/30 text-[#a78bfa] text-xs font-semibold tracking-wide uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-[#a78bfa] animate-pulse" />
            <span>{badge}</span>
          </div>

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#18181b] border border-[#27272a] text-xs text-[#a1a1aa]">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="font-mono text-amber-300 font-medium">
              {mastery}% mastery
            </span>
            <span className="text-[#71717a]">· {statusText}</span>
          </div>
        </div>

        {/* Heading & Student Rationale */}
        <div className="flex flex-col gap-3 max-w-3xl">
          <h3 className="text-2xl sm:text-[28px] font-bold text-white tracking-tight leading-snug">
            {headline}
          </h3>
          <p className="text-base sm:text-lg text-[#fafafa] leading-relaxed">
            {description}
          </p>
        </div>

        {/* Parameters Strip */}
        <div className="flex flex-wrap items-center gap-y-2 gap-x-6 text-sm text-[#a1a1aa] font-mono py-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-[#a78bfa]">
              format_list_numbered
            </span>
            <span>{questionCount} targeted questions</span>
          </div>
          <span className="text-[#52525b]">·</span>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-[#a78bfa]">
              schedule
            </span>
            <span>~{estimatedMinutes} minutes</span>
          </div>
        </div>

        {/* Action Row & Explanatory Disclosure */}
        <div className="pt-2 flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={() => onStartPractice?.('adaptive')}
              className="inline-flex items-center justify-center gap-2 bg-[#a78bfa] hover:bg-[#c4b5fd] text-[#0a0012] font-semibold px-6 py-3 rounded-lg transition-colors duration-150 text-sm shadow-sm cursor-pointer"
            >
              <span>Start adaptive practice</span>
              <span className="material-symbols-outlined text-[18px]">
                arrow_forward
              </span>
            </button>

            <button
              type="button"
              onClick={() => setWhyThisOpen((prev) => !prev)}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-[#a1a1aa] hover:text-white transition-colors rounded-lg hover:bg-[#18181b] cursor-pointer"
              aria-expanded={whyThisOpen}
            >
              <span>Why this?</span>
              <span
                className={`material-symbols-outlined text-[16px] transition-transform duration-200 ${
                  whyThisOpen ? 'rotate-180' : ''
                }`}
              >
                expand_more
              </span>
            </button>
          </div>

          {/* Collapsible Educational Rationale Disclosure */}
          {whyThisOpen && (
            <div className="rounded-lg bg-[#18181b] border border-[#27272a] p-4 text-sm text-[#a1a1aa] leading-relaxed max-w-2xl animate-in fade-in duration-150">
              <div className="flex items-start gap-2.5">
                <span className="material-symbols-outlined text-[20px] text-[#a78bfa] shrink-0 mt-0.5">
                  info
                </span>
                <p>{whyThis}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

