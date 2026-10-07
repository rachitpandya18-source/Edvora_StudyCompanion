import React from 'react';

/**
 * LearningMapPreview
 * Displays a clean, hierarchical preview of topic relationships in the course.
 * Uses student-friendly phrasing and status indicators.
 */
export default function LearningMapPreview({
  learningMap,
  onOpenLearningMap,
}) {
  const footnote =
    learningMap?.footnote ||
    'See how the topics in this course connect and what to learn next.';

  return (
    <section className="lg:col-span-7 rounded-xl border border-[#222227] bg-[#121215] p-6 space-y-5">
      <div className="flex items-center justify-between border-b border-[#222227] pb-4">
        <div>
          <h3 className="text-xl sm:text-[22px] font-bold text-white tracking-tight">
            Learning map
          </h3>
          <p className="text-[14px] text-[#a1a1aa] mt-0.5">
            See how topics in your course connect.
          </p>
        </div>
        {/* Action */}
        <button
          type="button"
          onClick={() => onOpenLearningMap?.()}
          className="inline-flex items-center gap-1 text-[13px] font-medium text-[#a78bfa] hover:text-[#9065f6] transition-colors focus:outline-none"
        >
          <span>Open learning map</span>
          <span className="material-symbols-outlined text-[15px]">arrow_forward</span>
        </button>
      </div>

      {/* Simple Concept Relationship Visualization */}
      <div className="bg-[#18181c] border border-[#222227] rounded-lg p-5">
        <div className="space-y-2">
          {/* Level 1: Arrays */}
          <div className="flex items-center gap-3">
            <div className="px-3.5 py-1.5 rounded-md bg-[#121215] border border-[#2e2e36] text-[15px] font-medium text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#34d399]" />
              <span>Arrays</span>
            </div>
            <span className="text-xs font-mono text-[#71717a]">
              Prerequisite mastered
            </span>
          </div>

          {/* Connector 1 */}
          <div className="pl-5 text-[#3f3f46] leading-none select-none text-[15px] font-mono">
            &darr;
          </div>

          {/* Level 2: Linked Lists */}
          <div className="flex items-center gap-3">
            <div className="px-3.5 py-1.5 rounded-md bg-[#121215] border border-[#2e2e36] text-[15px] font-medium text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#34d399]" />
              <span>Linked Lists</span>
            </div>
            <span className="text-xs font-mono text-[#71717a]">
              Pointers &amp; dynamic chains
            </span>
          </div>

          {/* Connector 2 */}
          <div className="pl-5 text-[#3f3f46] leading-none select-none text-[15px] font-mono">
            &darr;
          </div>

          {/* Level 3: Trees Branching */}
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="px-3.5 py-1.5 rounded-md bg-[#121215] border border-[#a78bfa]/40 text-[15px] font-medium text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#a78bfa]" />
                <span>Trees</span>
              </div>
              <span className="text-xs font-mono text-[#a78bfa]">
                Hierarchical data
              </span>
            </div>

            {/* Branches */}
            <div className="pl-6 space-y-2 border-l border-[#2e2e36] ml-4 mt-2 pt-1">
              <div className="flex items-center gap-3 relative before:content-[''] before:absolute before:-left-6 before:top-3 before:w-4 before:h-px before:bg-[#2e2e36]">
                <div className="px-3 py-1 rounded-md bg-[#121215] border border-[#2e2e36] text-[14px] text-[#e4e4e7] flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#34d399]" />
                  <span>Binary Trees</span>
                </div>
                <span className="text-[12px] font-mono text-[#71717a]">
                  BST property
                </span>
              </div>

              <div className="flex items-center gap-3 relative before:content-[''] before:absolute before:-left-6 before:top-3 before:w-4 before:h-px before:bg-[#2e2e36]">
                <div className="px-3 py-1 rounded-md bg-[#121215] border border-[#fbbf24]/50 text-[14px] text-white flex items-center gap-2 ring-1 ring-[#fbbf24]/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#fbbf24]" />
                  <span className="font-medium">AVL Trees</span>
                </div>
                <span className="text-[12px] font-mono text-[#fbbf24]">
                  Rotations &amp; balance invariant
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Student-facing descriptive note */}
      <p className="text-[13px] text-[#71717a] font-mono">
        {footnote}
      </p>
    </section>
  );
}

