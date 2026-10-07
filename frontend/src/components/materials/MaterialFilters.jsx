import React from 'react';

/**
 * MaterialFilters
 * Segmented filter tabs and responsive search input.
 */
export default function MaterialFilters({
  activeFilter = 'all',
  onSelectFilter,
  searchQuery = '',
  onSearchChange,
}) {
  const filters = [
    { id: 'all', label: 'All' },
    { id: 'pdf', label: 'PDFs' },
    { id: 'slides', label: 'Slides' },
    { id: 'lectures', label: 'Lectures' },
  ];

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
      {/* Segmented Filter Pills */}
      <div className="inline-flex p-1 bg-[#121215] border border-[#27272a] rounded-lg gap-1 shrink-0">
        {filters.map((flt) => {
          const isActive = activeFilter === flt.id;
          return (
            <button
              key={flt.id}
              type="button"
              onClick={() => onSelectFilter?.(flt.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors cursor-pointer ${
                isActive
                  ? 'bg-[#1e1e22] text-[#fafafa] border border-[#27272a] shadow-sm font-semibold'
                  : 'text-[#a1a1aa] hover:text-[#fafafa]'
              }`}
            >
              {flt.label}
            </button>
          );
        })}
      </div>

      {/* Search Input */}
      <div className="relative w-full sm:w-72">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a] text-[18px]">
          search
        </span>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange?.(e.target.value)}
          placeholder="Search materials..."
          className="w-full pl-9 pr-3 py-1.5 text-xs bg-[#121215] border border-[#27272a] rounded-lg text-[#fafafa] placeholder:text-[#71717a] focus:outline-none focus:border-[#a78bfa] focus:ring-1 focus:ring-[#a78bfa] transition-all"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => onSearchChange?.('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#71717a] hover:text-white text-xs"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

