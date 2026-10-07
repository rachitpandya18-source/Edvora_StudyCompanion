export default function CourseNavigation({
  activeSection = 'overview',
  onSelectSection,
}) {
  const sections = [
    { id: 'overview', label: 'Overview' },
    { id: 'tutor', label: 'Tutor' },
    { id: 'practice', label: 'Practice' },
    { id: 'materials', label: 'Materials' },
    { id: 'progress', label: 'Progress' },
  ];

  return (
    <div className="border-b border-[#222227] mb-8">
      <nav className="flex items-center gap-8 -mb-px overflow-x-auto" aria-label="Course Navigation">
        {sections.map((section) => {
          const isActive = activeSection === section.id;

          return (
            <button
              key={section.id}
              type="button"
              onClick={() => onSelectSection && onSelectSection(section.id)}
              className={`pb-3 text-[16px] font-medium transition-colors flex items-center gap-2 cursor-pointer bg-transparent border-0 border-b-2 shrink-0 ${
                isActive
                  ? 'text-white border-[#a78bfa]'
                  : 'text-[#a1a1aa] hover:text-white border-transparent'
              }`}
            >
              <span>{section.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

