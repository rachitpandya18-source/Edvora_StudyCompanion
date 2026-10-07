import React from 'react';

/**
 * OutsideMaterialNotice
 * Demonstrates the boundary between course-grounded information and general knowledge.
 * Styled with Edvora amber attention accents without looking like an error.
 */
export default function OutsideMaterialNotice({
  courseName = 'Data Structures & Algorithms',
  onAnswerGenerally,
  onStayCourseOnly,
}) {
  return (
    <div className="flex items-start gap-3.5 max-w-3xl">
      <div className="w-8 h-8 rounded-full bg-amber-500/10 border border-amber-500/40 flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
        <span className="material-symbols-outlined text-base">shield</span>
      </div>

      <div className="bg-[#121215] border border-amber-500/30 rounded-2xl rounded-tl-sm p-4 text-sm max-w-xl space-y-3 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1 font-mono">
            <span className="material-symbols-outlined text-xs">warning</span>
            Outside Your Course Material
          </span>
        </div>

        <p className="text-xs text-[#a1a1aa] leading-relaxed">
          I couldn&apos;t find B-Tree database indexing comparisons in the uploaded materials for{' '}
          <strong className="text-[#fafafa] font-semibold">{courseName}</strong>. This course focuses primarily on in-memory binary search structures (AVL, Red-Black).
        </p>

        <p className="text-xs text-[#fafafa] font-medium">
          Would you like me to answer using general computer science knowledge, or keep strictly to your course syllabus?
        </p>

        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            onClick={onAnswerGenerally}
            className="px-3 py-1.5 rounded text-xs font-medium bg-[#a78bfa] text-[#0a0012] hover:bg-[#c4b5fd] transition-colors cursor-pointer"
          >
            Answer generally
          </button>
          <button
            type="button"
            onClick={onStayCourseOnly}
            className="px-3 py-1.5 rounded text-xs font-medium bg-[#18181b] border border-[#27272a] text-[#fafafa] hover:text-[#a78bfa] hover:border-[#a78bfa]/40 transition-colors cursor-pointer"
          >
            Stay course-only
          </button>
        </div>
      </div>
    </div>
  );
}

