import React, { useState } from 'react';
import MaterialCard from '../components/materials/MaterialCard';
import MaterialFilters from '../components/materials/MaterialFilters';
import AddMaterialModal from '../components/materials/AddMaterialModal';
import MaterialPreviewModal from '../components/materials/MaterialPreviewModal';
import { defaultCourseMaterials } from '../data/mockMaterialsData';

/**
 * CourseMaterialsPage
 * Course Materials library workspace.
 * Displays all course documents, slides, and lecture recordings with search, filtering,
 * live readiness statuses, dynamic counts, and upload flow.
 */
export default function CourseMaterialsPage({
  _courseName = 'Data Structures & Algorithms',
}) {
  const [materials, setMaterials] = useState(defaultCourseMaterials);
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [previewMaterial, setPreviewMaterial] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Dynamic summary counts calculated directly from materials state
  const pdfCount = materials.filter((m) => m.type.toLowerCase() === 'pdf').length;
  const slideCount = materials.filter(
    (m) => m.type.toLowerCase() === 'ppt' || m.type.toLowerCase() === 'pptx'
  ).length;
  const lectureCount = materials.filter((m) =>
    ['video', 'mp4', 'mov', 'webm'].includes(m.type.toLowerCase())
  ).length;

  // Filter and search logic
  const filteredMaterials = materials.filter((mat) => {
    // 1. Category Filter
    if (activeFilter === 'pdf' && mat.type.toLowerCase() !== 'pdf') {
      return false;
    }
    if (
      activeFilter === 'slides' &&
      !['ppt', 'pptx'].includes(mat.type.toLowerCase())
    ) {
      return false;
    }
    if (
      activeFilter === 'lectures' &&
      !['video', 'mp4', 'mov', 'webm'].includes(mat.type.toLowerCase())
    ) {
      return false;
    }

    // 2. Search Query (filename or metadata)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const matchName = mat.filename.toLowerCase().includes(q);
      const matchMeta = mat.metadata?.toLowerCase().includes(q);
      if (!matchName && !matchMeta) {
        return false;
      }
    }

    return true;
  });

  // Add material handler with simulated processing -> ready transition
  const handleConfirmAddMaterials = (newFiles) => {
    const newItems = newFiles.map((file, idx) => ({
      id: `mat-new-${Date.now()}-${idx}`,
      type: file.type,
      filename: file.name,
      metadata: `${file.sizeText} · Added just now`,
      status: 'processing',
      addedAt: 'Just now',
      actionLabel:
        file.type === 'pdf'
          ? 'Open PDF'
          : ['ppt', 'pptx'].includes(file.type)
          ? 'Open slides'
          : 'Play lecture',
      previewContent: {
        title: file.name,
        excerpt:
          'Newly uploaded course file. Topics extracted and integrated into course workspace.',
      },
    }));

    // Add to list immediately
    setMaterials((prev) => [...newItems, ...prev]);
    showToast(`Added ${newItems.length} material${newItems.length === 1 ? '' : 's'}. Edvora is preparing them...`);

    // Simulate transition to Ready after 2.8 seconds
    setTimeout(() => {
      setMaterials((prev) =>
        prev.map((m) => {
          if (newItems.some((ni) => ni.id === m.id)) {
            return {
              ...m,
              status: 'ready',
              metadata: m.metadata.replace('Added just now', 'Indexed and ready'),
            };
          }
          return m;
        })
      );
      showToast('All new materials are now ready to use in your course!');
    }, 2800);
  };

  const handleRemoveMaterial = (id) => {
    setMaterials((prev) => prev.filter((m) => m.id !== id));
    showToast('Material removed from course library.');
  };

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-lg bg-[#18181b] border border-[#a78bfa]/50 text-xs font-mono text-white shadow-xl animate-in fade-in slide-in-from-bottom duration-200">
          {toastMessage}
        </div>
      )}

      {/* Page Header Cluster */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-4xl md:text-[42px] font-bold text-white tracking-tight leading-tight">
            Materials
          </h2>
          <p className="text-base text-[#a1a1aa] mt-1.5">
            Your course materials, organized and ready to learn from.
          </p>

          {/* Dynamic counts */}
          <div className="inline-flex items-center gap-2 mt-3 text-xs text-[#a1a1aa] font-medium font-mono">
            <span className="text-white">{pdfCount} {pdfCount === 1 ? 'PDF' : 'PDFs'}</span>
            <span className="text-[#52525b]">·</span>
            <span className="text-white">{slideCount} {slideCount === 1 ? 'slide deck' : 'slide decks'}</span>
            <span className="text-[#52525b]">·</span>
            <span className="text-white">{lectureCount} {lectureCount === 1 ? 'lecture' : 'lectures'}</span>
          </div>
        </div>

        {/* Add Material Secondary Action */}
        <button
          type="button"
          onClick={() => setIsAddModalOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-[#121215] border border-[#27272a] hover:border-[#a78bfa]/50 hover:bg-[#18181b] rounded-lg transition-all duration-150 cursor-pointer self-start md:self-end"
        >
          <span className="material-symbols-outlined text-[16px] text-[#a78bfa]">
            add
          </span>
          <span>Add material</span>
        </button>
      </div>

      {/* Subtle Grounding Context Banner */}
      <div className="rounded-lg p-3.5 bg-[#0f0f12] border border-[#27272a] flex items-center gap-3 shadow-sm">
        <div className="w-8 h-8 rounded-lg bg-[#121215] flex items-center justify-center shrink-0 border border-[#27272a] text-[#a78bfa]">
          <span className="material-symbols-outlined text-[18px]">verified</span>
        </div>
        <p className="text-xs text-[#a1a1aa] leading-relaxed">
          Edvora uses these materials to ground your tutor, practice and personalized recommendations.
        </p>
      </div>

      {/* Filter Controls & Search Bar */}
      <MaterialFilters
        activeFilter={activeFilter}
        onSelectFilter={setActiveFilter}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Materials List */}
      <div className="space-y-3 pt-1">
        {filteredMaterials.length > 0 ? (
          filteredMaterials.map((material) => (
            <MaterialCard
              key={material.id}
              material={material}
              onOpenPreview={setPreviewMaterial}
              onRemove={handleRemoveMaterial}
            />
          ))
        ) : (
          /* Clean Empty Search State */
          <div className="p-12 text-center rounded-xl bg-[#121215] border border-[#27272a] space-y-3">
            <div className="w-12 h-12 rounded-xl bg-[#18181b] border border-[#27272a] flex items-center justify-center mx-auto text-[#71717a]">
              <span className="material-symbols-outlined text-2xl">search_off</span>
            </div>
            <h4 className="text-base font-semibold text-white">No materials found</h4>
            <p className="text-xs text-[#a1a1aa] max-w-sm mx-auto">
              No course files matched &ldquo;{searchQuery}&rdquo; in the current filter. Try a different search query or select &ldquo;All&rdquo;.
            </p>
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setActiveFilter('all');
              }}
              className="mt-2 px-3 py-1.5 text-xs rounded-lg bg-[#18181b] border border-[#27272a] text-[#a78bfa] hover:text-white transition-colors cursor-pointer"
            >
              Reset filters
            </button>
          </div>
        )}
      </div>

      {/* Add Material Modal */}
      <AddMaterialModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onConfirmAdd={handleConfirmAddMaterials}
      />

      {/* Material Preview Modal */}
      <MaterialPreviewModal
        isOpen={Boolean(previewMaterial)}
        material={previewMaterial}
        onClose={() => setPreviewMaterial(null)}
      />
    </div>
  );
}

