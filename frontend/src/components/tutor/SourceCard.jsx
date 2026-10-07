import React, { useEffect, useRef } from 'react';

/**
 * SourceCard
 * Renders a student-friendly course source item (PDF, PPT, or Video).
 * Highlights when active and supports auto-scrolling into view.
 */
export default function SourceCard({
  source,
  isActive = false,
  onSelect,
}) {
  const cardRef = useRef(null);

  useEffect(() => {
    if (isActive && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [isActive]);

  const getBadgeStyle = (type) => {
    switch (type) {
      case 'PDF':
        return 'bg-red-500/20 text-red-300 border-red-500/30';
      case 'PPT':
      case 'PPTX':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'VIDEO':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      default:
        return 'bg-[#27272a] text-[#a1a1aa] border-[#3f3f46]';
    }
  };

  return (
    <div
      ref={cardRef}
      id={`source-${source.number}`}
      onClick={() => onSelect && onSelect(source.number)}
      className={`p-3.5 rounded-lg bg-[#121215] border transition-all cursor-pointer ${
        isActive
          ? 'border-[#a78bfa] shadow-lg shadow-[#a78bfa]/5 ring-1 ring-[#a78bfa]/30'
          : 'border-[#27272a] hover:border-[#3f3f46]'
      }`}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-2 mb-2.5">
        <div className="flex items-center gap-2">
          <span
            className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${getBadgeStyle(
              source.type
            )}`}
          >
            {source.type}
          </span>
          <span className="font-medium text-xs text-[#fafafa]">
            [{source.number}] {source.title}
          </span>
        </div>

        {source.isVideo ? (
          <button
            type="button"
            className="px-2 py-1 rounded bg-[#18181b] border border-[#27272a] text-xs text-[#a78bfa] hover:border-[#a78bfa] transition-colors flex items-center gap-1 font-medium shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              // Mock action
            }}
          >
            <span className="material-symbols-outlined text-xs">play_arrow</span>
            <span>{source.actionText || 'Play'}</span>
          </button>
        ) : (
          <span className="text-xs text-[#a78bfa] hover:underline flex items-center gap-1 font-medium shrink-0">
            {source.actionText || 'View'}
          </span>
        )}
      </div>

      {/* Diagram (e.g. for Slide 18) */}
      {source.diagram && (
        <div className="bg-[#09090b] rounded border border-[#27272a] overflow-hidden mb-3">
          <div className="p-2.5 text-center border-b border-[#27272a]/70">
            <h4 className="text-xs font-bold text-[#fafafa]">{source.diagram.title}</h4>
            <p className="text-[10px] text-[#a1a1aa] font-mono mt-0.5">
              {source.diagram.condition}
            </p>
          </div>

          {/* Tree Visualization Graphic */}
          <div className="relative w-full max-w-[280px] h-28 mx-auto my-2 flex items-center justify-center">
            {/* Root Node 20 */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 flex flex-col items-center">
              <div className="w-7 h-7 rounded-full bg-[#121215] border-2 border-[#a78bfa] text-[#a78bfa] flex items-center justify-center text-xs font-bold font-mono">
                20
              </div>
              <span className="text-[9px] font-mono text-red-400">BF: +2</span>
            </div>

            {/* Left branch line */}
            <div className="absolute top-5 left-28 w-12 h-7 border-t-2 border-l-2 border-[#27272a] -rotate-45" />

            {/* Child Node 10 */}
            <div className="absolute top-10 left-16 flex flex-col items-center">
              <div className="w-7 h-7 rounded-full bg-[#121215] border border-[#52525b] text-[#fafafa] flex items-center justify-center text-xs font-bold font-mono">
                10
              </div>
              <span className="text-[9px] font-mono text-amber-400">BF: -1</span>
            </div>

            {/* Subtree line to 15 */}
            <div className="absolute top-14 left-28 w-7 h-7 border-t-2 border-r-2 border-amber-400/80 rotate-45" />

            {/* Elbow Node 15 */}
            <div className="absolute top-20 left-32 flex flex-col items-center">
              <div className="w-6 h-6 rounded-full bg-amber-500/20 border-2 border-amber-400 text-amber-300 flex items-center justify-center text-[11px] font-bold font-mono">
                15
              </div>
            </div>

            {/* Right Subtree T3 ghost */}
            <div className="absolute top-10 right-16 flex flex-col items-center opacity-40">
              <div className="w-6 h-6 rounded-full border border-dashed border-[#52525b] flex items-center justify-center text-[10px] font-mono text-[#a1a1aa]">
                T3
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quote / Excerpt */}
      {source.quote && (
        <blockquote className="text-xs text-[#fafafa] italic border-l-2 border-[#a78bfa] pl-2.5 leading-relaxed">
          &ldquo;{source.quote}&rdquo;
        </blockquote>
      )}

      {/* Description */}
      {source.description && (
        <p className="text-xs text-[#a1a1aa] leading-relaxed">
          {source.description}
        </p>
      )}
    </div>
  );
}

