export default function CourseMasteryList({ topics = [] }) {
  return (
    <section className="rounded-xl border border-[#222227] bg-[#121215] p-6 space-y-5">
      <div className="border-b border-[#222227] pb-4">
        <h3 className="text-xl sm:text-[22px] font-bold text-white tracking-tight">
          Course mastery
        </h3>
        <p className="text-[14px] text-[#a1a1aa] mt-0.5">
          Topic-level breakdown of your learning
        </p>
      </div>

      {/* Topic Rows */}
      <div className="space-y-3.5">
        {topics.map((topic) => {
          const isAttention = topic.variant === 'attention';
          const isDeveloping = topic.variant === 'developing';

          const statusColor = isAttention
            ? '#fbbf24'
            : isDeveloping
            ? '#a78bfa'
            : '#34d399';

          return (
            <div
              key={topic.id}
              className={`p-3.5 rounded-lg bg-[#18181c] border transition-colors flex items-center justify-between gap-4 ${
                isAttention
                  ? 'border-[#fbbf24]/30 hover:border-[#fbbf24]/50'
                  : 'border-[#222227] hover:border-[#2e2e36]'
              }`}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2 truncate">
                    <span className="text-[16px] font-medium text-white truncate">
                      {topic.name}
                    </span>
                    {topic.isStudyNext && (
                      <span className="text-[11px] font-mono bg-[#fbbf24]/10 text-[#fbbf24] px-1.5 py-0.5 rounded border border-[#fbbf24]/20 shrink-0">
                        Study Next
                      </span>
                    )}
                  </div>

                  <span
                    className="text-[13px] font-mono font-medium flex items-center gap-1.5 shrink-0 ml-2"
                    style={{ color: statusColor }}
                  >
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ backgroundColor: statusColor }}
                    />
                    {topic.status} · {topic.percentage}%
                  </span>
                </div>

                <div className="w-full h-1.5 bg-[#09090b] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${topic.percentage}%`,
                      backgroundColor: statusColor,
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
