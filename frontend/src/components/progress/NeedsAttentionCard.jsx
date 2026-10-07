import React from 'react';

/**
 * NeedsAttentionCard
 * Highlights weak topics, provides pedagogical diagnosis,
 * recommended next step, and direct action triggers for practice & tutoring.
 */
export default function NeedsAttentionCard({
  data,
  onStartPractice,
  onAskTutor,
}) {
  const {
    topic = 'AVL Trees',
    mastery = 43,
    description = 'Recent answers suggest difficulty with Left-Right and Right-Left rotations.',
    recommendedNextStep = 'Review AVL rotations → Practice 3 targeted questions',
    footnote = 'Based on your recent assessment and tutoring activity.',
    practiceActionLabel = 'Start adaptive practice',
    tutorActionLabel = 'Ask Tutor about rotations →',
  } = data || {};

  return (
    <div className="bg-[#121215] rounded-xl border border-[#27272a] p-6 space-y-4 shadow-sm">
      {/* Card Header */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-amber-400 tracking-wider uppercase font-mono">
          Needs Attention
        </span>
        <span className="text-xs text-[#a1a1aa] font-mono">
          Priority Focus
        </span>
      </div>

      {/* Main Focus Topic & Diagnosis */}
      <div>
        <h4 className="text-lg font-bold text-white tracking-tight">
          {topic} · {mastery}% mastery
        </h4>
        <p className="text-xs text-[#a1a1aa] mt-1.5 leading-relaxed">
          {description}
        </p>
      </div>

      {/* Focus Next Action Box */}
      <div className="p-3.5 rounded-lg bg-[#18181b]/80 border border-[#27272a]/80 space-y-1.5">
        <div className="text-[11px] font-semibold text-[#a1a1aa] tracking-wider uppercase font-mono">
          Recommended Next Step
        </div>
        <p className="text-xs font-medium text-white">
          {recommendedNextStep}
        </p>
        <p className="text-[11px] text-[#71717a]">
          {footnote}
        </p>
      </div>

      {/* Action CTAs */}
      <div className="pt-1 flex flex-col gap-2.5">
        <button
          type="button"
          onClick={onStartPractice}
          className="w-full py-2.5 px-4 rounded-lg bg-[#a78bfa] text-[#0a0012] font-semibold text-xs hover:bg-[#c4b5fd] transition-colors flex items-center justify-center gap-1.5 shadow-sm active:scale-[0.99]"
        >
          <span>{practiceActionLabel}</span>
          <span className="material-symbols-outlined text-sm">arrow_forward</span>
        </button>

        <button
          type="button"
          onClick={onAskTutor}
          className="text-xs text-[#a78bfa] hover:text-[#c4b5fd] transition-colors text-center py-1 font-medium"
        >
          {tutorActionLabel}
        </button>
      </div>
    </div>
  );
}

