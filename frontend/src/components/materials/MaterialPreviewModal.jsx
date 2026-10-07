import React from 'react';

/**
 * MaterialPreviewModal
 * Lightweight preview modal for inspecting course PDFs, slides, or lecture videos.
 */
export default function MaterialPreviewModal({
  isOpen = false,
  material = null,
  onClose,
}) {
  if (!isOpen || !material) return null;

  const { filename, type, metadata, previewContent } = material;

  const getTypeBadge = () => {
    switch (type?.toLowerCase()) {
      case 'pdf':
        return {
          label: 'PDF Document',
          style: 'bg-red-500/20 text-red-300 border-red-500/30',
          icon: 'picture_as_pdf',
        };
      case 'ppt':
      case 'pptx':
        return {
          label: 'Slide Deck',
          style: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
          icon: 'slideshow',
        };
      case 'video':
      case 'mp4':
      case 'mov':
      case 'webm':
        return {
          label: 'Lecture Recording',
          style: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
          icon: 'smart_display',
        };
      default:
        return {
          label: 'Course Document',
          style: 'bg-zinc-800 text-zinc-300 border-zinc-700',
          icon: 'description',
        };
    }
  };

  const badge = getTypeBadge();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-2xl bg-[#0c0c0f] border border-[#27272a] rounded-xl shadow-2xl z-10 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="h-14 px-6 border-b border-[#27272a] flex items-center justify-between bg-[#0f0f12] shrink-0">
          <div className="flex items-center gap-2.5 min-w-0 pr-3">
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold shrink-0 ${badge.style}`}
            >
              {badge.label}
            </span>
            <h3 className="text-sm font-semibold text-white tracking-tight truncate">
              {filename}
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer shrink-0"
            aria-label="Close preview"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div className="flex items-center justify-between text-xs text-[#a1a1aa] font-mono pb-2 border-b border-[#27272a]">
            <span>{metadata}</span>
            <span className="text-[#34d399] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#34d399]" />
              Ready
            </span>
          </div>

          {/* Simulated Viewer Surface */}
          <div className="rounded-xl border border-[#27272a] bg-[#121215] p-6 space-y-4 shadow-inner">
            <div className="flex items-center gap-2 text-[#a78bfa]">
              <span className="material-symbols-outlined text-xl">{badge.icon}</span>
              <h4 className="text-base font-semibold text-white">
                {previewContent?.title || filename}
              </h4>
            </div>

            {/* Document / Media Preview Block */}
            <div className="p-4 rounded-lg bg-[#09090b] border border-[#27272a] text-sm text-[#fafafa] leading-relaxed">
              <p className="italic text-[#a1a1aa]">
                &ldquo;{previewContent?.excerpt || 'Document contents processed and available for grounded answers.'}&rdquo;
              </p>
            </div>

            {type === 'video' && (
              <div className="w-full h-36 bg-[#09090b] rounded-lg border border-[#27272a] flex flex-col items-center justify-center gap-2 text-center text-[#71717a]">
                <span className="material-symbols-outlined text-3xl text-[#6366f1]">
                  play_circle
                </span>
                <span className="text-xs font-mono text-[#a1a1aa]">
                  Simulated Player · {previewContent?.duration || '52:00'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 px-6 border-t border-[#27272a] bg-[#0f0f12] flex items-center justify-between gap-3 shrink-0">
          <span className="text-[11px] text-[#71717a]">
            Preview mode. Full document viewer connects in Phase 2.
          </span>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#18181b] hover:bg-[#202026] border border-[#27272a] text-xs font-medium text-white transition-colors cursor-pointer"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}

