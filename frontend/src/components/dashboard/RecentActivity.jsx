export default function RecentActivity({ activities = [] }) {
  return (
    <div className="pt-6 border-t border-[#222227]">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white tracking-tight">Recent Activity</h3>
        <span className="text-xs font-mono text-[#71717a]">Chronological feed</span>
      </div>

      <div className="space-y-3">
        {activities.map((activity) => {
          const isStrong = activity.variant === 'strong';
          const isAccent = activity.variant === 'accent';

          return (
            <div
              key={activity.id}
              className="p-3.5 rounded-xl bg-[#121215] border border-[#222227] flex items-start gap-3.5"
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                  isStrong
                    ? 'bg-emerald-400/15 text-emerald-400'
                    : isAccent
                    ? 'bg-[#a78bfa]/15 text-[#a78bfa]'
                    : 'bg-[#18181c] text-zinc-400'
                }`}
              >
                <span className="material-symbols-outlined text-[15px]">
                  {activity.icon}
                </span>
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-zinc-200">{activity.title}</p>
                <div className="flex items-center gap-2 text-xs font-mono text-[#71717a] mt-0.5 truncate">
                  <span className="text-zinc-300">{activity.course}</span>
                  <span>•</span>
                  <span>{activity.detail}</span>
                  <span>•</span>
                  <span>{activity.time}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

