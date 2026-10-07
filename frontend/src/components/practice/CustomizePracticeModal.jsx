import React, { useState } from 'react';

/**
 * CustomizePracticeModal
 * Clean developer-grade dialog for tailored assessment configurations.
 * Supports Question Type, Topic, Difficulty, and Count.
 */
export default function CustomizePracticeModal({
  isOpen = false,
  onClose,
  onStartCustomPractice,
}) {
  const [selectedType, setSelectedType] = useState('mixed');
  const [selectedTopic, setSelectedTopic] = useState('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState('adaptive');
  const [selectedCount, setSelectedCount] = useState(10);

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
    { id: 'avl', label: 'AVL Trees (Needs attention)' },
    { id: 'trees', label: 'Trees & BST' },
    { id: 'linked_lists', label: 'Linked Lists' },
    { id: 'arrays', label: 'Arrays' },
  ];

  const difficulties = [
    { id: 'adaptive', label: 'Adaptive (Calibrated to Mastery)' },
    { id: 'foundational', label: 'Foundational' },
    { id: 'standard', label: 'Standard' },
    { id: 'challenging', label: 'Challenging' },
  ];

  const counts = [5, 10, 15, 20];

  const handleSubmit = (e) => {
    e.preventDefault();
    onStartCustomPractice?.({
      type: selectedType,
      topic: selectedTopic,
      difficulty: selectedDifficulty,
      count: selectedCount,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-xl bg-[#0c0c0f] border border-[#27272a] rounded-xl shadow-2xl z-10 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="h-14 px-6 border-b border-[#27272a] flex items-center justify-between bg-[#0f0f12] shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[#a78bfa] text-xl">
              tune
            </span>
            <h3 className="text-base font-semibold text-white tracking-tight">
              Customize Practice
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
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
            className="px-4 py-2 rounded-lg border border-[#27272a] text-xs font-medium text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            className="px-5 py-2 rounded-lg bg-[#a78bfa] hover:bg-[#c4b5fd] text-[#0a0012] text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <span>Start custom practice</span>
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  );
}

