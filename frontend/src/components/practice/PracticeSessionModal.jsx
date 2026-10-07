import React, { useState } from 'react';

/**
 * PracticeSessionModal
 * High-fidelity frontend simulation modal for launched practice sessions.
 * Clearly communicates the practice session parameters without calling the backend.
 */
export default function PracticeSessionModal({
  isOpen = false,
  sessionConfig = null,
  onClose,
}) {
  const [sampleAnswer, setSampleAnswer] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen || !sessionConfig) return null;

  const {
    title = 'Adaptive Practice Session',
    topic = 'AVL Trees',
    questionCount = 5,
    estimatedMinutes = 8,
    difficulty = 'Adaptive',
    type = 'Multiple Choice & Conceptual',
  } = sessionConfig;

  // Realistic sample question for the demo
  const sampleQuestion = {
    qNum: 1,
    prompt:
      'Given an AVL tree with root node 20 (Balance Factor: +2) whose left child is node 10 (Balance Factor: -1), which rotation sequence is required to restore height balance?',
    options: [
      { id: 'a', text: 'Single Right Rotation on node 20' },
      { id: 'b', text: 'Single Left Rotation on node 10' },
      {
        id: 'c',
        text: 'Left-Right Double Rotation: Left rotation on node 10, followed by Right rotation on node 20',
        isCorrect: true,
      },
      { id: 'd', text: 'Right-Left Double Rotation: Right rotation on node 20, followed by Left rotation on node 10' },
    ],
    explanation:
      'Correct! An "inner elbow" (Left-Right) imbalance occurs when the root has BF +2 and its left child has BF -1. A left rotation on the child straightens the elbow, and a subsequent right rotation on the root restores the balance invariant.',
  };

  const handleSelectOption = (optId) => {
    if (!submitted) {
      setSampleAnswer(optId);
    }
  };

  const handleSubmitAnswer = () => {
    if (sampleAnswer) {
      setSubmitted(true);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Card */}
      <div className="relative w-full max-w-2xl bg-[#0c0c0f] border border-[#27272a] rounded-xl shadow-2xl z-10 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="h-14 px-6 border-b border-[#27272a] flex items-center justify-between bg-[#0f0f12] shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-[#34d399] animate-pulse" />
            <h3 className="text-sm font-semibold text-white tracking-tight">
              {title}
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
            aria-label="Close practice session"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Parameter Strip */}
          <div className="p-3.5 rounded-lg bg-[#121215] border border-[#27272a] flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-[#a1a1aa]">
            <div className="flex items-center gap-2">
              <span className="text-[#a78bfa] font-semibold">Topic:</span>
              <span className="text-white">{topic}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#a78bfa] font-semibold">Questions:</span>
              <span className="text-white">1 of {questionCount}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#a78bfa] font-semibold">Time:</span>
              <span className="text-white">~{estimatedMinutes}m</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#a78bfa] font-semibold">Difficulty:</span>
              <span className="text-white">{difficulty}</span>
            </div>
          </div>

          {/* Interactive Question Card */}
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-mono text-[#a1a1aa]">
              <span>Question {sampleQuestion.qNum} of {questionCount}</span>
              <span className="px-2 py-0.5 rounded bg-[#18181b] border border-[#27272a] text-[#a78bfa]">
                {type}
              </span>
            </div>

            <p className="text-[15px] font-medium text-white leading-relaxed">
              {sampleQuestion.prompt}
            </p>

            {/* Options */}
            <div className="space-y-2.5 pt-1">
              {sampleQuestion.options.map((opt) => {
                const isSelected = sampleAnswer === opt.id;
                const isCorrect = opt.isCorrect;

                let borderStyle = 'border-[#27272a] hover:border-[#3f3f46] bg-[#121215] text-[#fafafa]';
                if (submitted) {
                  if (isCorrect) {
                    borderStyle = 'border-[#34d399] bg-[#065f46]/20 text-[#34d399]';
                  } else if (isSelected && !isCorrect) {
                    borderStyle = 'border-[#ef4444] bg-[#ef4444]/10 text-[#ef4444]';
                  }
                } else if (isSelected) {
                  borderStyle = 'border-[#a78bfa] bg-[#18181c] text-white ring-1 ring-[#a78bfa]/30';
                }

                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleSelectOption(opt.id)}
                    className={`w-full p-3.5 rounded-lg border text-left text-xs sm:text-sm font-medium transition-all flex items-start gap-3 cursor-pointer ${borderStyle}`}
                  >
                    <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center shrink-0 mt-0.5 text-xs font-mono font-bold uppercase">
                      {opt.id}
                    </span>
                    <span className="flex-1 leading-snug">{opt.text}</span>
                  </button>
                );
              })}
            </div>

            {/* Feedback on submission */}
            {submitted && (
              <div className="p-4 rounded-lg bg-[#18181b] border border-[#34d399]/40 text-xs sm:text-sm text-[#fafafa] space-y-1.5 animate-in fade-in duration-150">
                <div className="flex items-center gap-1.5 text-[#34d399] font-semibold">
                  <span className="material-symbols-outlined text-base">check_circle</span>
                  <span>Feedback</span>
                </div>
                <p className="text-[#a1a1aa] leading-relaxed">
                  {sampleQuestion.explanation}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-[#27272a] bg-[#0f0f12] flex items-center justify-between gap-3 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-[#27272a] text-xs font-medium text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
          >
            End Practice Session
          </button>

          {!submitted ? (
            <button
              type="button"
              disabled={!sampleAnswer}
              onClick={handleSubmitAnswer}
              className="px-5 py-2 rounded-lg bg-[#a78bfa] hover:bg-[#c4b5fd] text-[#0a0012] disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <span>Submit Answer</span>
              <span className="material-symbols-outlined text-sm">check</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2 rounded-lg bg-[#34d399] hover:bg-[#6ee7b7] text-[#003318] text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <span>Finish Demo Practice</span>
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

