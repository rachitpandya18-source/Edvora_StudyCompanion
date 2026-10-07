import React from 'react';

/**
 * CustomizePractice
 * Horizontal card offering custom practice configuration.
 */
export default function CustomizePractice({ onOpenCustomize }) {
  return (
    <section className="rounded-xl border border-[#27272a] bg-[#0f0f12] p-6 lg:p-7 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-sm">
      <div className="flex flex-col gap-1 max-w-xl">
        <h4 className="text-lg font-semibold text-white">
          Want something specific?
        </h4>
        <p className="text-[15px] text-[#a1a1aa] leading-relaxed">
          Choose specific question types (MCQ, Short Answer, Numerical), select topics, or adjust question count.
        </p>
      </div>

      <div className="shrink-0">
        <button
          type="button"
          onClick={onOpenCustomize}
          className="inline-flex items-center gap-2 border border-[#27272a] hover:border-[#a78bfa] text-white font-medium px-5 py-2.5 rounded-lg transition-colors text-sm hover:bg-[#18181b] cursor-pointer"
        >
          <span>Customize your practice</span>
          <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
        </button>
      </div>
    </section>
  );
}

