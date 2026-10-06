export default function StudyNextCard({
  studyNext,
  onStart,
  onViewCourse,
}) {
  const {
    courseName,
    topic,
    mastery,
    status,
    rationale,
    recommendedActions,
  } = studyNext;

  return (
    <div className="p-6 rounded-2xl bg-[#121215] border border-[#222227] relative overflow-hidden shadow-lg">
      {/* Subtle top accent gradient */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-400 via-[#a78bfa] to-transparent" />

      {/* Header Info */}
      <div className="flex items-start justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-medium tracking-wider text-amber-300 uppercase bg-amber-400/15 px-2 py-0.5 rounded">
              Study next
            </span>
            <span className="text-xs font-mono text-[#a1a1aa]">{courseName}</span>
          </div>
          <h2 className="text-2xl font-semibold text-white tracking-tight">{topic}</h2>
        </div>

        {/* Status Badge */}
        <div className="text-right">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-400/15 text-amber-300 border border-amber-400/20 text-xs font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            {status}
          </span>
          <span className="block text-xs font-mono text-[#71717a] mt-1">{mastery}% mastery</span>
        </div>
      </div>

      {/* Recommendation Rationale ("Why this?") */}
      <div className="p-3.5 rounded-xl bg-[#18181c]/80 border border-[#222227] mb-5">
        <span className="text-xs font-mono text-[#71717a] block uppercase mb-1">
          Why this?
        </span>
        <p className="text-sm text-zinc-300 leading-relaxed">
          &ldquo;{rationale}&rdquo;
        </p>
      </div>

      {/* Structured Action Sequence */}
      <div className="space-y-2.5 mb-6">
        <span className="text-xs font-mono text-[#71717a] uppercase tracking-wider block">
          Recommended action
        </span>

        <div className="space-y-2">
          {recommendedActions.map((action) => (
            <div
              key={action.id}
              className="flex items-center gap-3 p-3 rounded-lg bg-[#0f0f12] border border-[#222227] text-sm"
            >
              <span className="w-5 h-5 rounded-full bg-[#a78bfa]/15 text-[#a78bfa] font-mono text-xs flex items-center justify-center shrink-0 font-medium">
                {action.step}
              </span>
              <span className="text-zinc-200 font-medium">{action.title}</span>
              <span className="text-xs font-mono text-[#71717a] ml-auto">
                {action.durationOrPage}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-3 pt-2 border-t border-[#222227]">
        <button
          type="button"
          onClick={() => onStart && onStart(studyNext)}
          className="flex-1 py-2.5 px-4 rounded-lg bg-primary text-[#0a0012] font-semibold text-sm hover:bg-primary-fixed-dim transition-colors flex items-center justify-center gap-2 cursor-pointer border-0 shadow-sm"
        >
          <span>Start</span>
          <span className="material-symbols-outlined text-[17px]">arrow_forward</span>
        </button>

        <button
          type="button"
          onClick={() => onViewCourse && onViewCourse(studyNext)}
          className="py-2.5 px-4 rounded-lg bg-[#18181c] hover:bg-[#202026] border border-[#2e2e36] text-zinc-300 hover:text-white font-medium text-sm transition-colors cursor-pointer"
        >
          View course
        </button>
      </div>
    </div>
  );
}

