export default function SelectedMaterialList({ materials = [], onRemoveMaterial }) {
  if (materials.length === 0) {
    return null;
  }

  const getFileIcon = (type) => {
    switch (type) {
      case 'pdf':
        return {
          icon: 'picture_as_pdf',
          color: 'text-red-400',
        };
      case 'ppt':
      case 'pptx':
        return {
          icon: 'slideshow',
          color: 'text-amber-400',
        };
      case 'video':
      case 'mp4':
      case 'mov':
        return {
          icon: 'play_circle',
          color: 'text-primary',
        };
      default:
        return {
          icon: 'description',
          color: 'text-zinc-400',
        };
    }
  };

  return (
    <div className="mt-8 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-1">
        <h3 className="text-sm font-semibold tracking-tight text-white uppercase font-mono">
          Added materials ({materials.length})
        </h3>
        <p className="text-xs text-[#a1a1aa]">
          You can add more material to this course anytime.
        </p>
      </div>

      {/* Materials List */}
      <div className="space-y-2.5">
        {materials.map((mat) => {
          const { icon, color } = getFileIcon(mat.type);
          const isReady = mat.status === 'Ready';

          return (
            <div
              key={mat.id}
              className="flex items-center justify-between p-4 rounded-xl border border-[#27272a] bg-[#0f0f12] hover:bg-[#121215] transition-colors group"
            >
              <div className="flex items-center gap-3.5 min-w-0">
                <div className="w-10 h-10 rounded-lg bg-[#18181c] border border-[#27272a] flex items-center justify-center shrink-0">
                  <span className={`material-symbols-outlined text-[20px] ${color}`}>
                    {icon}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-[15px] sm:text-[16px] font-medium text-white truncate pr-2">
                    {mat.name}
                  </p>
                  <p className="text-[13px] text-[#a1a1aa] font-mono mt-0.5 truncate">
                    {mat.sizeText}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0 ml-2">
                {isReady ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium font-mono bg-[#065f46]/30 text-emerald-400 border border-[#065f46]">
                    <span className="material-symbols-outlined text-[14px]">check</span>
                    Ready
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium font-mono bg-[#27272a] text-primary border border-primary/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                    Processing...
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => onRemoveMaterial && onRemoveMaterial(mat.id)}
                  aria-label={`Remove ${mat.name}`}
                  className="text-[#a1a1aa] hover:text-red-400 transition-colors p-1 rounded-md hover:bg-[#18181c] cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

