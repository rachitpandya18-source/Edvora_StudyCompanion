export default function CourseStudyNext({
  studyNext,
  onStartSession,
  onViewTopic,
}) {
  const {
    topic = 'AVL Trees',
    mastery = 43,
    statusText = 'Needs attention',
    whyThis = 'You recently struggled with Left-Right and Right-Left rotations.',
    recommendedActions = [
      { id: '1', icon: 'menu_book', title: 'Review AVL rotations' },
      { id: '2', icon: 'fact_check', title: 'Practice 3 targeted questions', accent: 'success' },
    ],
    estimatedTime = '12 min',
  } = studyNext || {};

  return (
    <section className="rounded-xl border border-[#2e2e36] bg-[#121215] p-7 relative overflow-hidden shadow-2xl">
      {/* Subtle top accent line */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#a78bfa] via-[#fbbf24] to-transparent" />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-4 max-w-2xl">
          {/* Eyebrow Tag */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-[#a78bfa] bg-[#a78bfa]/10 px-2.5 py-1 rounded-md border border-[#a78bfa]/25">
              Study Next
            </span>
            <span className="text-xs font-mono text-[#71717a]">
              Personalized recommendation
            </span>
          </div>

          {/* Topic & State */}
          <div>
            <div className="flex flex-wrap items-baseline gap-3">
              <h2 className="text-2xl sm:text-[28px] font-bold text-white tracking-tight">
                {topic}
              </h2>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm px-2 py-0.5 rounded bg-[#fbbf24]/10 text-[#fbbf24] border border-[#fbbf24]/20 font-medium">
                  {mastery}% mastery
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[#fbbf24]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#fbbf24]" />
                  {statusText}
                </span>
              </div>
            </div>

            {/* Why this? Section */}
            <div className="mt-3 text-[15px] sm:text-[16px] text-[#d4d4d8] leading-relaxed bg-[#18181c]/80 border border-[#222227] rounded-lg p-3.5">
              <span className="font-semibold text-white mr-1.5">Why this?</span>
              <span className="text-[#a1a1aa]">&ldquo;{whyThis}&rdquo;</span>
            </div>
          </div>

          {/* Recommended Actions Roadmap */}
          <div className="pt-1">
            <span className="text-xs font-mono uppercase tracking-wider text-[#71717a] block mb-2 font-medium">
              Recommended actions:
            </span>
            <div className="grid sm:grid-cols-2 gap-2.5">
              {recommendedActions.map((action) => (
                <div
                  key={action.id}
                  className={`flex items-center gap-3 bg-[#18181c] border border-[#222227] px-3.5 py-2.5 rounded-lg text-[15px] ${
                    action.accent === 'success' ? 'text-[#34d399]' : 'text-[#e4e4e7]'
                  }`}
                >
                  <span
                    className={`material-symbols-outlined text-[18px] ${
                      action.accent === 'success' ? 'text-[#34d399]' : 'text-[#a78bfa]'
                    }`}
                  >
                    {action.icon}
                  </span>
                  <span>{action.title}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Actions Block */}
        <div className="lg:border-l lg:border-[#222227] lg:pl-8 flex flex-col justify-center items-start lg:items-stretch gap-4 shrink-0 min-w-[240px]">
          <div className="flex items-center gap-2 text-[14px] font-mono text-[#a1a1aa]">
            <span className="material-symbols-outlined text-[18px] text-[#71717a]">
              schedule
            </span>
            <span>
              Estimated time: <strong className="text-white font-semibold">{estimatedTime}</strong>
            </span>
          </div>

          {/* Primary CTA */}
          <button
            type="button"
            onClick={onStartSession}
            className="w-full inline-flex items-center justify-center gap-2 bg-[#a78bfa] hover:bg-[#9065f6] text-[#09090b] font-semibold text-[15px] sm:text-[16px] px-5 py-3 rounded-lg transition-all duration-150 shadow-lg shadow-[#a78bfa]/15 active:scale-[0.99] cursor-pointer border-0"
          >
            <span>Start adaptive session</span>
            <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
          </button>

          {/* Secondary Action */}
          <button
            type="button"
            onClick={onViewTopic}
            className="w-full inline-flex items-center justify-center gap-1.5 text-[14px] font-medium text-[#a1a1aa] hover:text-white py-1.5 transition-colors cursor-pointer bg-transparent border-0"
          >
            <span>View topic</span>
            <span className="material-symbols-outlined text-[16px]">chevron_right</span>
          </button>
        </div>
      </div>
    </section>
  );
}

