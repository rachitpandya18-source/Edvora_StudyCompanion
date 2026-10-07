import React from 'react';

/**
 * FollowUpActions
 * Follow-up action chips allowing students to quickly drill down into the explanation.
 */
export default function FollowUpActions({ onSelectAction }) {
  const actions = [
    { id: 'simpler', label: 'Explain simpler', icon: 'lightbulb' },
    { id: 'example', label: 'Give an example', icon: 'code' },
    { id: 'stepbystep', label: 'Explain step-by-step', icon: 'format_list_numbered' },
    { id: 'quiz', label: 'Ask me a question', iconEmoji: '🎯', isPrimary: true },
  ];

  return (
    <div className="flex flex-wrap items-center gap-2 pt-1 pl-1">
      {actions.map((act) => (
        <button
          key={act.id}
          type="button"
          onClick={() => onSelectAction && onSelectAction(act.id, act.label)}
          className={`px-2.5 py-1 text-xs rounded-full border transition-all flex items-center gap-1.5 cursor-pointer ${
            act.isPrimary
              ? 'bg-[#a78bfa]/10 border-[#a78bfa]/30 text-[#a78bfa] hover:bg-[#a78bfa]/20 font-medium'
              : 'bg-[#121215] border-[#27272a] text-[#fafafa] hover:border-[#a78bfa]/60 hover:text-[#a78bfa]'
          }`}
        >
          {act.iconEmoji ? (
            <span className="text-xs">{act.iconEmoji}</span>
          ) : (
            <span className="material-symbols-outlined text-xs text-[#a1a1aa]">
              {act.icon}
            </span>
          )}
          <span>{act.label}</span>
        </button>
      ))}
    </div>
  );
}

