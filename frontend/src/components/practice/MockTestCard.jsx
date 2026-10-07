import React from 'react';

/**
 * MockTestCard
 * Comprehensive timed examination simulation across all course topics.
 */
export default function MockTestCard({
  courseName = 'Data Structures & Algorithms',
  mockTestData,
  onStartPractice,
}) {
  const {
    title = 'Mock Test',
    description = `Simulate a timed exam across all covered topics in ${courseName}.`,
    metadata = 'Timed · Comprehensive · Exam conditions',
  } = mockTestData || {};

  return (
    <div className="rounded-xl border border-[#27272a] bg-[#121215] p-6 lg:p-7 flex flex-col justify-between hover:border-[#3f3f46] transition-colors shadow-sm">
      <div className="flex flex-col gap-4">
        <div className="w-10 h-10 rounded-lg bg-[#18181b] border border-[#27272a] flex items-center justify-center text-[#a78bfa]">
          <span className="material-symbols-outlined text-[22px]">assignment</span>
        </div>

        <div className="flex flex-col gap-2">
          <h4 className="text-xl sm:text-[22px] font-semibold text-white tracking-tight">
            {title}
          </h4>
          <p className="text-sm sm:text-base text-[#a1a1aa] leading-normal">
            {description}
          </p>
        </div>

        <div className="text-xs font-mono text-[#71717a] pt-1 flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px]">fact_check</span>
          <span>{metadata}</span>
        </div>
      </div>

      <div className="pt-6">
        <button
          type="button"
          onClick={() => onStartPractice?.('mock-test')}
          className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-5 py-2.5 rounded-lg border border-[#27272a] text-[#fafafa] text-sm font-medium hover:bg-[#18181b] hover:border-[#3f3f46] transition-colors cursor-pointer"
        >
          <span>Start mock test</span>
          <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
        </button>
      </div>
    </div>
  );
}

