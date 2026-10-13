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
        {(!learningMap?.nodes || learningMap.nodes.length === 0) ? (
          <div className="text-center py-6 text-xs font-mono text-[#71717a]">
            Curriculum learning map will appear here once topics and concepts are established.
          </div>
        ) : (
          <div className="space-y-3">
            {learningMap.nodes.map((node, idx) => (
              <React.Fragment key={node.id || idx}>
                <div className="flex items-center gap-3">
                  <div className="px-3.5 py-1.5 rounded-md bg-[#121215] border border-[#2e2e36] text-[15px] font-medium text-white flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        node.status === 'strong'
                          ? 'bg-[#34d399]'
                          : node.status === 'attention'
                          ? 'bg-[#fbbf24]'
                          : 'bg-[#a78bfa]'
                      }`}
                    />
                    <span>{node.title}</span>
                  </div>
                  {node.note && (
                    <span className="text-xs font-mono text-[#71717a]">
                      {node.note}
                    </span>
                  )}
                </div>
                {idx < learningMap.nodes.length - 1 && (
                  <div className="pl-5 text-[#3f3f46] leading-none select-none text-[15px] font-mono">
                    &darr;
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>

      {/* Student-facing descriptive note */}
      <p className="text-[13px] text-[#71717a] font-mono">
        {footnote}
      </p>
    </section>
  );
}

