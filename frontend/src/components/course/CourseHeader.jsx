export default function CourseHeader({
  courseName = 'Data Structures & Algorithms',
  mastery = 68,
  onBack,
}) {
  return (
    <div>
      {/* Top Breadcrumb / Return Path */}
      <div className="flex items-center justify-between mb-4">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 text-[14px] font-medium text-[#a1a1aa] hover:text-white transition-colors group cursor-pointer bg-transparent border-0 p-0"
        >
          <span className="material-symbols-outlined text-[18px] group-hover:-translate-x-0.5 transition-transform">
            arrow_back
          </span>
          <span>Back to Dashboard</span>
        </button>
      </div>

      {/* Course Header (Primary Identity & Progress) */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 pt-2">
        <div>
          {/* Course Name only (no code/credits/professor) */}
          <h1 className="text-4xl sm:text-[44px] font-bold tracking-tight text-white leading-tight">
            {courseName}
          </h1>

          {/* Course-level status: ONLY Mastery */}
          <div className="flex items-center gap-4 mt-3">
            <span className="text-[16px] text-[#a1a1aa]">Course mastery</span>
            <div className="flex items-center gap-3">
              <div className="w-36 h-2 rounded-full bg-[#18181c] border border-[#2e2e36] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#a78bfa] to-[#818cf8] rounded-full transition-all duration-300"
                  style={{ width: `${mastery}%` }}
                />
              </div>
              <span className="font-mono text-base font-semibold text-white">
                {mastery}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

