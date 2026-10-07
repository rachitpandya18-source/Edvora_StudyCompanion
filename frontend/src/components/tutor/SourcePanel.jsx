import React, { useEffect } from 'react';
import SourceCard from './SourceCard';

/**
 * SourcePanel
 * Clean, reusable, collapsible source viewer.
 * Supports desktop sidebar mode and mobile drawer/overlay mode.
 */
export default function SourcePanel({
  sources = [],
  activeSource = null,
  isOpen = true,
  onClose,
  onSelectSource,
  isMobile = false,
}) {
  // ESC shortcut to close panel
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const content = (
    <div className="flex flex-col h-full bg-[#0c0c0f] border-l border-[#27272a] overflow-hidden select-none">
      {/* Viewer Header */}
      <div className="h-12 px-4 border-b border-[#27272a] flex items-center justify-between bg-[#0f0f12] shrink-0">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[#fafafa]">
            Sources
          </h2>
          <p className="text-[11px] text-[#a1a1aa]">
            {sources.length} sources used in this answer
          </p>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="text-[#a1a1aa] hover:text-[#fafafa] p-1.5 rounded hover:bg-[#18181b] transition-colors cursor-pointer"
          title="Collapse Sources (Esc)"
          aria-label="Collapse Sources panel"
        >
          <span className="material-symbols-outlined text-base">vertical_split</span>
        </button>
      </div>

      {/* Scrollable Source Cards Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {sources.map((src) => (
          <SourceCard
            key={src.id || src.number}
            source={src}
            isActive={activeSource === src.number}
            onSelect={onSelectSource}
          />
        ))}
      </div>

      {/* Viewer Footer */}
      <div className="p-3 border-t border-[#27272a] bg-[#0f0f12] flex items-center justify-between shrink-0">
        <span className="text-[11px] text-[#a1a1aa]">
          Press{' '}
          <kbd className="px-1 py-0.5 bg-[#1e1e22] rounded text-[10px] font-mono border border-[#27272a]">
            ESC
          </kbd>{' '}
          to collapse
        </span>

        <button
          type="button"
          onClick={onClose}
          className="px-2.5 py-1 text-xs rounded bg-[#18181b] border border-[#27272a] text-[#fafafa] hover:text-[#a78bfa] hover:border-[#a78bfa]/50 transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <span className="material-symbols-outlined text-sm">view_sidebar</span>
          <span>Full Conversation</span>
        </button>
      </div>
    </div>
  );

  // If mobile, wrap in full-height slide-over drawer with backdrop
  if (isMobile) {
    return (
      <div className="fixed inset-0 z-50 flex justify-end">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-xs transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Drawer panel */}
        <div className="relative w-full max-w-md h-full z-10 shadow-2xl animate-in slide-in-from-right duration-200">
          {content}
        </div>
      </div>
    );
  }

  // Desktop inline pane (~38%)
  return (
    <aside className="w-[38%] flex flex-col h-full shrink-0 transition-all duration-200">
      {content}
    </aside>
  );
}

