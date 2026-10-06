export default function LearningSnapshot({ snapshot }) {
  const {
    strongCount = 8,
    developingCount = 5,
    attentionCount = 3,
  } = snapshot || {};

  return (
    <div className="p-6 rounded-2xl bg-[#121215] border border-[#222227] space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-mono uppercase tracking-widest text-[#71717a] block mb-0.5">
            Your Learning
          </span>
          <h3 className="text-lg font-semibold text-white tracking-tight">Overall Snapshot</h3>
        </div>
        <span className="text-xs font-mono text-[#71717a]">All courses</span>
      </div>

      {/* Concept Breakdown Grid */}
      <div className="grid grid-cols-3 gap-3">
        {/* Strong */}
        <div className="p-3.5 rounded-xl bg-[#0f0f12] border border-[#222227] flex flex-col justify-between">
          <div className="flex items-center gap-1.5 mb-2">
            <span className="w-2 h-2 rounded-full bg-[#34d399]" />
            <span className="text-xs font-mono text-[#71717a] uppercase">Strong</span>
          </div>
          <span className="text-2xl font-mono font-semibold text-white">{strongCount}</span>
          <span className="text-xs text-[#71717a] mt-0.5">concepts</span>
        </div>

        {/* Developing */}
        <div className="p-3.5 rounded-xl bg-[#0f0f12] border border-[#222227] flex flex-col justify-between">
          <div className="flex items-center gap-1.5 mb-2">
            <span className="w-2 h-2 rounded-full bg-[#a78bfa]" />
            <span className="text-xs font-mono text-[#71717a] uppercase">Developing</span>
          </div>
          <span className="text-2xl font-mono font-semibold text-white">{developingCount}</span>
          <span className="text-xs text-[#71717a] mt-0.5">concepts</span>
        </div>

        {/* Needs attention */}
        <div className="p-3.5 rounded-xl bg-[#0f0f12] border border-[#222227] flex flex-col justify-between">
          <div className="flex items-center gap-1.5 mb-2">
            <span className="w-2 h-2 rounded-full bg-[#fbbf24]" />
            <span className="text-xs font-mono text-amber-300 uppercase">Needs review</span>
          </div>
          <span className="text-2xl font-mono font-semibold text-amber-300">{attentionCount}</span>
          <span className="text-xs text-[#71717a] mt-0.5">concepts</span>
        </div>
      </div>
    </div>
  );
}

