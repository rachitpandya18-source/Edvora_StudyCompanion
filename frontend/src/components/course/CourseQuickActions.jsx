export default function CourseQuickActions({ onSelectAction }) {
  const actions = [
    {
      id: 'tutor',
      title: 'Ask your tutor',
      subtitle: 'Ask a question about this course',
      icon: 'chat_bubble',
      iconColor: 'text-[#a78bfa]',
      hoverBorder: 'hover:border-[#a78bfa]/50',
      hoverTitle: 'group-hover:text-[#a78bfa]',
    },
    {
      id: 'practice',
      title: 'Practice',
      subtitle: 'Test your understanding',
      icon: 'edit_note',
      iconColor: 'text-[#34d399]',
      hoverBorder: 'hover:border-[#34d399]/50',
      hoverTitle: 'group-hover:text-[#34d399]',
    },
    {
      id: 'materials',
      title: 'Browse materials',
      subtitle: 'Open your PDFs, slides and lectures',
      icon: 'folder_copy',
      iconColor: 'text-[#a1a1aa]',
      hoverBorder: 'hover:border-[#a1a1aa]/50',
      hoverTitle: 'group-hover:text-white',
    },
  ];

  return (
    <section className="rounded-xl border border-[#222227] bg-[#121215] p-6 space-y-4">
      <div className="border-b border-[#222227] pb-4">
        <h3 className="text-xl sm:text-[22px] font-bold text-white tracking-tight">
          Quick actions
        </h3>
        <p className="text-[14px] text-[#a1a1aa] mt-0.5">
          Jump directly into a course tool
        </p>
      </div>

      <div className="space-y-3">
        {actions.map((act) => (
          <button
            key={act.id}
            type="button"
            onClick={() => onSelectAction && onSelectAction(act.id)}
            className={`w-full group block p-4 rounded-lg bg-[#18181c] border border-[#222227] ${act.hoverBorder} hover:bg-[#202026] transition-all cursor-pointer text-left`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-lg bg-[#09090b] border border-[#2e2e36] ${act.iconColor} flex items-center justify-center transition-colors shrink-0`}>
                  <span className="material-symbols-outlined text-[20px]">{act.icon}</span>
                </div>
                <div>
                  <h4 className={`text-[16px] font-semibold text-white ${act.hoverTitle} transition-colors`}>
                    {act.title}
                  </h4>
                  <p className="text-[13px] text-[#a1a1aa] mt-0.5">{act.subtitle}</p>
                </div>
              </div>
              <span className="material-symbols-outlined text-[18px] text-[#71717a] group-hover:text-white group-hover:translate-x-0.5 transition-all mt-1">
                chevron_right
              </span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

