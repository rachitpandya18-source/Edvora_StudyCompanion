export default function CourseCard({
  course,
  onContinue,
}) {
  const {
    code,
    title,
    category,
    mastery,
    statusText,
    statusVariant,
    statusColor,
    currentlyLearning,
    lastStudied,
    materials,
  } = course;

  const isPrimary = statusVariant === 'attention' || mastery < 70;

  return (
    <div className="p-6 rounded-2xl bg-[#121215] border border-[#222227] hover:border-[#2e2e36] transition-all space-y-5">
      {/* Top Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <span
              className={`text-xs font-mono font-medium tracking-wider uppercase px-2 py-0.5 rounded ${
                statusVariant === 'strong'
                  ? 'bg-emerald-400/15 text-emerald-400'
                  : statusVariant === 'attention'
                  ? 'bg-[#a78bfa]/15 text-[#a78bfa]'
                  : 'bg-[#18181c] text-zinc-400'
              }`}
            >
              {code}
            </span>
            <span className="text-xs text-[#a1a1aa] font-mono flex items-center gap-1.5">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: statusColor || '#fbbf24' }}
              />
              {statusText}
            </span>
          </div>
          <h3 className="text-xl font-semibold text-white tracking-tight">{title}</h3>
          <p className="text-sm text-[#a1a1aa] mt-0.5">{category}</p>
        </div>

        {/* Mastery Percentage */}
        <div className="text-right shrink-0">
          <span className="text-2xl font-mono font-semibold text-white">{mastery}%</span>
          <span className="block text-xs font-mono text-[#71717a]">course mastery</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-[#18181c] h-1.5 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${mastery}%`,
            backgroundColor:
              statusVariant === 'strong'
                ? '#34d399'
                : statusVariant === 'attention'
                ? '#a78bfa'
                : '#71717a',
          }}
        />
      </div>

      {/* Context Info */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-sm border-t border-[#222227]">
        <div>
          <span className="text-xs font-mono text-[#71717a] block uppercase">
            Currently learning
          </span>
          <span className="font-medium text-zinc-200 flex items-center gap-1.5 mt-0.5">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: statusColor || '#fbbf24' }}
            />
            <span className="truncate">{currentlyLearning}</span>
          </span>
        </div>
        <div className="sm:text-right">
          <span className="text-xs font-mono text-[#71717a] block uppercase">
            Last studied
          </span>
          <span className="text-zinc-300 font-mono text-xs mt-1 block">
            {lastStudied}
          </span>
        </div>
      </div>

      {/* Card Actions & Counts */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-[#222227]">
        <div className="flex items-center gap-2.5 text-xs font-mono text-[#71717a]">
          <span>{materials.textbooks} Textbooks</span>
          <span>•</span>
          <span>{materials.slides} Slides</span>
          <span>•</span>
          <span>{materials.lectures} Lectures</span>
        </div>

        <div>
          <button
            type="button"
            onClick={() => onContinue && onContinue(course)}
            className={`w-full sm:w-auto px-4 py-2 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              isPrimary
                ? 'bg-primary text-[#0a0012] hover:bg-primary-fixed-dim font-semibold'
                : 'bg-[#18181c] hover:bg-[#202026] text-white border border-[#2e2e36]'
            }`}
          >
            <span>Continue</span>
            <span className="material-symbols-outlined text-[16px]">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  );
}

