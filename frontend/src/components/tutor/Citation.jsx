import React from 'react';

/**
 * Citation
 * Interactive, accessible inline citation badge (e.g. [1], [2]).
 * Clicking selects and highlights the corresponding source in the Sources panel.
 */
export default function Citation({
  number,
  onClick,
  title,
}) {
  return (
    <button
      type="button"
      onClick={() => onClick && onClick(number)}
      className="inline-flex items-center px-1.5 py-0.5 ml-1 text-xs font-mono font-medium rounded bg-[#18181b] border border-[#a78bfa]/60 text-[#a78bfa] hover:bg-[#a78bfa]/20 hover:border-[#a78bfa] transition-colors cursor-pointer select-none"
      title={title || `View source [${number}]`}
      aria-label={`View citation source ${number}`}
    >
      [{number}]
    </button>
  );
}

