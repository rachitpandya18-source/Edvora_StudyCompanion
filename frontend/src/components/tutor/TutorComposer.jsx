import React, { useState } from 'react';

/**
 * TutorComposer
 * Anchored input at the bottom of the conversation pane.
 */
export default function TutorComposer({ onSendMessage }) {
  const [text, setText] = useState('');
  const [attachmentNotice, setAttachmentNotice] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    onSendMessage?.(text.trim());
    setText('');
  };

  const handleAttachClick = () => {
    setAttachmentNotice(true);
    setTimeout(() => setAttachmentNotice(false), 2500);
  };

  return (
    <div className="p-4 border-t border-[#27272a] bg-[#0f0f12]">
      {attachmentNotice && (
        <div className="mb-2 px-3 py-1.5 rounded bg-[#18181b] border border-[#a78bfa]/30 text-xs text-[#a78bfa] flex items-center justify-between animate-in fade-in duration-150">
          <span>You can reference course materials directly in your question!</span>
          <button
            type="button"
            onClick={() => setAttachmentNotice(false)}
            className="text-[#a1a1aa] hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="relative flex items-center bg-[#121215] rounded-lg border border-[#27272a] focus-within:border-[#a78bfa] transition-all">
          {/* Attach Button Affordance */}
          <button
            type="button"
            onClick={handleAttachClick}
            className="p-2.5 text-[#a1a1aa] hover:text-[#fafafa] transition-colors cursor-pointer"
            title="Attach course reference"
            aria-label="Attach course reference"
          >
            <span className="material-symbols-outlined text-lg">attach_file</span>
          </button>

          {/* Text Input */}
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="w-full bg-transparent border-0 text-sm text-[#fafafa] placeholder:text-[#71717a] focus:outline-none focus:ring-0 px-2 py-3"
            placeholder="Ask something about this course..."
            aria-label="Ask a question about this course"
          />

          {/* Right Controls */}
          <div className="flex items-center gap-1.5 pr-2 shrink-0">
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-[#a1a1aa] bg-[#1e1e22] rounded border border-[#27272a]">
              ⌘K
            </kbd>

            <button
              type="submit"
              disabled={!text.trim()}
              className="w-8 h-8 rounded bg-[#a78bfa] text-[#0a0012] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center hover:bg-[#c4b5fd] transition-colors cursor-pointer"
              title="Send question"
              aria-label="Send question"
            >
              <span className="material-symbols-outlined text-base">arrow_upward</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

