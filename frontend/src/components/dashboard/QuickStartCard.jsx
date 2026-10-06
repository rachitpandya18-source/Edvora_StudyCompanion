export default function QuickStartCard({
  category,
  title,
  subtitle,
  icon,
  accent = 'accent',
  onClick,
}) {
  const isAttention = accent === 'attention';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group p-4 rounded-xl bg-[#121215] border transition-all flex flex-col justify-between h-36 cursor-pointer text-left w-full ${
        isAttention
          ? 'border-[#222227] hover:border-amber-400/50 hover:bg-[#18181c]'
          : 'border-[#222227] hover:border-[#a78bfa]/40 hover:bg-[#18181c]'
      }`}
    >
      <div className="flex items-start justify-between w-full">
        <span
          className={`text-[13px] font-mono uppercase tracking-wide ${
            isAttention ? 'text-amber-400' : 'text-[#a1a1aa]'
          }`}
        >
          {category}
        </span>
        <div
          className={`w-7 h-7 rounded-md flex items-center justify-center transition-transform group-hover:translate-x-0.5 ${
            isAttention
              ? 'bg-amber-400/15 text-amber-400'
              : accent === 'accent'
              ? 'bg-[#a78bfa]/15 text-[#a78bfa]'
              : 'bg-[#18181c] text-[#a1a1aa] group-hover:text-white'
          }`}
        >
          <span className="material-symbols-outlined text-[17px]">{icon}</span>
        </div>
      </div>

      <div>
        <h3
          className={`text-base font-semibold text-white transition-colors ${
            isAttention
              ? 'group-hover:text-amber-400'
              : 'group-hover:text-[#a78bfa]'
          }`}
        >
          {title}
        </h3>
        <p
          className={`text-[13px] truncate mt-0.5 ${
            isAttention ? 'text-amber-300/80 font-medium' : 'text-[#a1a1aa]'
          }`}
        >
          {subtitle}
        </p>
      </div>
    </button>
  );
}

