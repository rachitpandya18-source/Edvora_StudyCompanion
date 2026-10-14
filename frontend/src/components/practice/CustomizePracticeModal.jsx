import React, { useState, useEffect } from 'react';

/**
 * CustomizePracticeModal
 * Clean developer-grade dialog for tailored assessment configurations.
 * Supports Question Type, Topic, Difficulty, and Count.
 */
export default function CustomizePracticeModal({
  isOpen = false,
  onClose,
  onStartCustomPractice,
  topics: availableTopics = [],
}) {
  const [selectedType, setSelectedType] = useState('mixed');
  const [selectedTopic, setSelectedTopic] = useState('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState('adaptive');
  const [selectedCount, setSelectedCount] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isSubmitting) {
        onClose?.();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, isSubmitting]);

  if (!isOpen) return null;

  const questionTypes = [
    { id: 'mixed', label: 'Mixed', icon: 'shuffle' },
    { id: 'mcq', label: 'Multiple Choice (MCQ)', icon: 'check_box' },
    { id: 'true_false', label: 'True / False', icon: 'rule' },
    { id: 'short_answer', label: 'Short Answer', icon: 'short_text' },
    { id: 'numerical', label: 'Numerical / Trace', icon: 'calculate' },
  ];

  const topics = [
    { id: 'all', label: 'All Course Topics' },
    ...availableTopics.map((t) => ({
      id: t.id || t.title || t.name,
      label: t.title || t.name || t.id,
    })),
  ];

  const difficulties = [
    { id: 'adaptive', label: 'Adaptive (Calibrated to Mastery)' },
    { id: 'foundational', label: 'Foundational' },
    { id: 'standard', label: 'Standard' },
    { id: 'challenging', label: 'Challenging' },
  ];

  const counts = [5, 10, 15, 20];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await onStartCustomPractice?.({
        type: selectedType,
        topic: selectedTopic,
        difficulty: selectedDifficulty,
        count: selectedCount,
      });
    } catch (err) {
      setErrorMessage(
        err?.data?.detail ||
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to start custom practice.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-xs transition-opacity"
        onClick={() => !isSubmitting && onClose?.()}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="customize-practice-title"
        className="relative w-full max-w-xl bg-[#0c0c0f] border border-[#27272a] rounded-xl shadow-2xl z-10 overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="h-14 px-6 border-b border-[#27272a] flex items-center justify-between bg-[#0f0f12] shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[#a78bfa] text-xl">
              tune
            </span>
            <h3 id="customize-practice-title" className="text-base font-semibold text-white tracking-tight">
              Customize Practice
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer disabled:opacity-50"
            aria-label="Close dialog"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Error Banner */}
          {errorMessage && (
            <div role="alert" className="p-3 rounded-lg bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-start gap-2">
              <span className="material-symbols-outlined text-sm text-red-400 mt-0.5">error</span>
              <span>{errorMessage}</span>
            </div>
          )}
          {/* 1. Question Type */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[#a1a1aa] mb-2.5">
              Question Type
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {questionTypes.map((qType) => {
                const isSelected = selectedType === qType.id;
                return (
                  <button
                    key={qType.id}
                    type="button"
                    onClick={() => setSelectedType(qType.id)}
                    className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-xs font-medium text-left transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#18181c] border-[#a78bfa] text-white ring-1 ring-[#a78bfa]/30'
                        : 'bg-[#121215] border-[#27272a] text-[#a1a1aa] hover:border-[#3f3f46]'
                    }`}
                  >
                    <span
                      className={`material-symbols-outlined text-[18px] ${
                        isSelected ? 'text-[#a78bfa]' : 'text-[#71717a]'
                      }`}
                    >
                      {qType.icon}
                    </span>
                    <span>{qType.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Target Topic */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[#a1a1aa] mb-2.5">
              Topic
            </label>
            <div className="space-y-1.5">
              {topics.map((t) => {
                const isSelected = selectedTopic === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setSelectedTopic(t.id)}
                    className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#18181c] border-[#a78bfa] text-white ring-1 ring-[#a78bfa]/30'
                        : 'bg-[#121215] border-[#27272a] text-[#a1a1aa] hover:border-[#3f3f46]'
                    }`}
                  >
                    <span>{t.label}</span>
                    {isSelected && (
                      <span className="material-symbols-outlined text-sm text-[#a78bfa]">
                        check
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 3. Difficulty */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[#a1a1aa] mb-2.5">
              Difficulty
            </label>
            <div className="grid grid-cols-2 gap-2">
              {difficulties.map((diff) => {
                const isSelected = selectedDifficulty === diff.id;
                return (
                  <button
                    key={diff.id}
                    type="button"
                    onClick={() => setSelectedDifficulty(diff.id)}
                    className={`px-3 py-2 rounded-lg border text-xs font-medium text-center transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#18181c] border-[#a78bfa] text-white ring-1 ring-[#a78bfa]/30'
                        : 'bg-[#121215] border-[#27272a] text-[#a1a1aa] hover:border-[#3f3f46]'
                    }`}
                  >
                    {diff.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 4. Question Count */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[#a1a1aa] mb-2.5">
              Number of Questions
            </label>
            <div className="flex items-center gap-3">
              {counts.map((cnt) => {
                const isSelected = selectedCount === cnt;
                return (
                  <button
                    key={cnt}
                    type="button"
                    onClick={() => setSelectedCount(cnt)}
                    className={`flex-1 py-2 rounded-lg border text-xs font-mono font-medium text-center transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#18181c] border-[#a78bfa] text-white ring-1 ring-[#a78bfa]/30'
                        : 'bg-[#121215] border-[#27272a] text-[#a1a1aa] hover:border-[#3f3f46]'
                    }`}
                  >
                    {cnt}
                  </button>
                );
              })}
            </div>
          </div>
        </form>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-[#27272a] bg-[#0f0f12] flex items-center justify-end gap-3 shrink-0">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg border border-[#27272a] text-xs font-medium text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-5 py-2 rounded-lg bg-[#a78bfa] hover:bg-[#c4b5fd] text-[#0a0012] text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                <span>Generating session...</span>
              </>
            ) : (
              <>
                <span>Start custom practice</span>
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

