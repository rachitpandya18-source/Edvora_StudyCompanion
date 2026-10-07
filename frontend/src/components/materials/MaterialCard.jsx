import React from 'react';

/**
 * MaterialCard
 * Renders an individual course material item with student-facing status and actions.
 */
export default function MaterialCard({
  material,
  onOpenPreview,
  onRemove,
}) {
  const {
    id,
    type,
    filename,
    metadata,
    status = 'ready',
    actionLabel,
  } = material;

  const getTypeIconDetails = () => {
    switch (type.toLowerCase()) {
      case 'pdf':
        return {
          icon: 'picture_as_pdf',
          color: 'text-[#f43f5e]',
        };
      case 'ppt':
      case 'pptx':
        return {
          icon: 'slideshow',
          color: 'text-[#f59e0b]',
        };
      case 'video':
      case 'mp4':
      case 'mov':
      case 'webm':
        return {
          icon: 'smart_display',
          color: 'text-[#6366f1]',
        };
      default:
        return {
          icon: 'description',
          color: 'text-[#a1a1aa]',
        };
    }
  };

  const { icon, color } = getTypeIconDetails();
  const isProcessing = status === 'processing';

  return (
    <div className="p-4 rounded-xl bg-[#121215] border border-[#27272a] hover:border-[#3f3f46] transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4 group">
      <div className="flex items-start gap-4 min-w-0">
        {/* File Type Icon */}
        <div className="w-10 h-10 rounded-lg bg-[#18181b] border border-[#27272a] flex items-center justify-center shrink-0">
          <span className={`material-symbols-outlined text-[22px] ${color}`}>
            {icon}
          </span>
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1">
          <div className="text-[17px] font-medium text-white group-hover:text-[#a78bfa] transition-colors tracking-tight truncate pr-2">
            {filename}
          </div>
          <div className="text-xs text-[#a1a1aa] mt-1 truncate">
            {metadata}
          </div>

          {/* Student-facing Readiness Status */}
          <div className="flex items-center gap-1.5 mt-2 text-[11px]">
            {isProcessing ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] animate-pulse" />
                <span className="text-[#f59e0b] font-medium">
                  Edvora is preparing this material
                </span>
              </>
            ) : status === 'attention' ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span className="text-amber-400 font-medium">
                  Needs attention
                </span>
              </>
            ) : (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-[#34d399]" />
                <span className="text-[#a1a1aa]">
                  Ready to use in your course
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div className="flex items-center gap-2 self-end md:self-center shrink-0">
        {onRemove && (
          <button
            type="button"
            onClick={() => onRemove(id)}
            className="p-1.5 text-[#71717a] hover:text-red-400 transition-colors rounded-lg hover:bg-[#18181b] cursor-pointer"
            title="Remove material"
            aria-label={`Remove ${filename}`}
          >
            <span className="material-symbols-outlined text-[18px]">delete</span>
          </button>
        )}

        {isProcessing ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#71717a] bg-[#09090b] border border-[#27272a]/60 rounded-lg cursor-not-allowed select-none">
            <span>Processing...</span>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => onOpenPreview?.(material)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-[#18181b] hover:bg-[#202026] border border-[#27272a] hover:border-[#a78bfa]/50 rounded-lg transition-colors cursor-pointer"
          >
            <span>{actionLabel || 'Open material'}</span>
            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
          </button>
        )}
      </div>
    </div>
  );
}

