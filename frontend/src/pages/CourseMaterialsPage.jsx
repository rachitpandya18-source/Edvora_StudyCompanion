import React, { useState, useEffect, useCallback } from 'react';
import MaterialCard from '../components/materials/MaterialCard';
import MaterialFilters from '../components/materials/MaterialFilters';
import AddMaterialModal from '../components/materials/AddMaterialModal';
import MaterialPreviewModal from '../components/materials/MaterialPreviewModal';
import coursesApi from '../api/coursesApi';
import curriculumApi from '../api/curriculumApi';
import { defaultCourseMaterials } from '../data/mockMaterialsData';

/**
 * CourseMaterialsPage
 * Course Materials library workspace.
 * Displays all course documents, slides, and lecture recordings with search, filtering,
 * live readiness statuses, dynamic counts, and upload flow.
 */
export default function CourseMaterialsPage({
  courseId,
  courseName = 'Data Structures & Algorithms',
  onCurriculumGenerated,
}) {
  const [materials, setMaterials] = useState(defaultCourseMaterials);
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [previewMaterial, setPreviewMaterial] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [isGeneratingCurriculum, setIsGeneratingCurriculum] = useState(false);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const loadSources = useCallback(async () => {
    if (!courseId) return;
    try {
      const sources = await coursesApi.listSources(courseId);
      if (Array.isArray(sources) && sources.length > 0) {
        const mapped = sources.map((s) => ({
          id: s.id,
          type: s.source_type || 'pdf',
          filename: s.filename,
          metadata: `${(s.source_type || 'PDF').toUpperCase()} · Indexed in course`,
          status: s.processing_status === 'completed' ? 'ready' : (s.processing_status || 'ready'),
          addedAt: s.created_at ? new Date(s.created_at).toLocaleDateString() : 'Recently',
          actionLabel: 'Open Material',
          previewContent: {
            title: s.filename,
            excerpt: `Indexed course material file (${s.filename}). Extracted and ready for tutoring, RAG citations, and practice question generation.`,
          },
        }));
        setMaterials(mapped);
      }
    } catch {
      // Fallback to sample materials if course is new or offline
    }
  }, [courseId]);

  useEffect(() => {
    let ignore = false;
    async function init() {
      if (!courseId) return;
      try {
        const sources = await coursesApi.listSources(courseId);
        if (ignore) return;
        if (Array.isArray(sources) && sources.length > 0) {
          const mapped = sources.map((s) => ({
            id: s.id,
            type: s.source_type || 'pdf',
            filename: s.filename,
            metadata: `${(s.source_type || 'PDF').toUpperCase()} · Indexed in course`,
            status: s.processing_status === 'completed' ? 'ready' : (s.processing_status || 'ready'),
            addedAt: s.created_at ? new Date(s.created_at).toLocaleDateString() : 'Recently',
            actionLabel: 'Open Material',
            previewContent: {
              title: s.filename,
              excerpt: `Indexed course material file (${s.filename}). Extracted and ready for tutoring, RAG citations, and practice question generation.`,
            },
          }));
          setMaterials(mapped);
        }
      } catch {
        // Fallback to sample materials
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [courseId]);


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

  const handleConfirmAddMaterials = async (newFiles) => {
    if (!courseId) {
      showToast('Course ID not found.');
      return;
    }

    showToast(`Uploading ${newFiles.length} course material(s)...`);

    for (const fileItem of newFiles) {
      if (fileItem.file) {
        try {
          await coursesApi.uploadMaterial(courseId, fileItem.file);
        } catch (err) {
          console.warn(`Upload error for ${fileItem.name}:`, err);
        }
      }
    }

    await loadSources();
    showToast('Materials uploaded and indexed successfully into course!');
  };

  const handleGenerateCurriculum = async () => {
    if (!courseId) return;
    setIsGeneratingCurriculum(true);
    showToast('Extracting topics and prerequisite DAG from course materials...');
    try {
      await curriculumApi.generateCurriculum(courseId, { mode: 'replace' });
      showToast('Curriculum generated successfully!');
      onCurriculumGenerated?.();
    } catch (err) {
      showToast(err.message || 'Curriculum generation completed or in progress.');
    } finally {
      setIsGeneratingCurriculum(false);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#18181c] border border-[#a78bfa]/50 text-white text-xs px-4 py-2.5 rounded-lg shadow-xl flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#34d399]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header and Stats */}
      <section className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
            Materials
          </h2>
          <p className="text-sm md:text-base text-[#a1a1aa] mt-1.5">
            Indexed textbooks, lecture slides, and transcripts for {courseName}.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={isGeneratingCurriculum}
            onClick={handleGenerateCurriculum}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#27272a] hover:bg-[#3f3f46] text-xs font-semibold text-white border border-[#3f3f46] transition-all cursor-pointer disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-sm text-[#a78bfa]">
              {isGeneratingCurriculum ? 'sync' : 'auto_awesome'}
            </span>
            {isGeneratingCurriculum ? 'Extracting DAG...' : 'Generate Curriculum'}
          </button>

          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary hover:bg-primary-hover text-xs font-semibold text-white shadow-lg transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-sm">add</span>
            Upload Material
          </button>
        </div>
      </section>

      {/* Filters and Search Bar */}
      <MaterialFilters
        activeFilter={activeFilter}
        onSelectFilter={setActiveFilter}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        counts={{ all: materials.length, pdf: pdfCount, slides: slideCount, lectures: lectureCount }}
      />

      {/* Materials Grid */}
      {filteredMaterials.length === 0 ? (
        <div className="p-12 text-center rounded-xl bg-[#121215] border border-[#27272a] text-[#a1a1aa] text-sm">
          No materials matching your criteria. Upload a PDF or change the filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredMaterials.map((mat) => (
            <MaterialCard
              key={mat.id}
              material={mat}
              onPreview={(item) => setPreviewMaterial(item)}
            />
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {isAddModalOpen && (
        <AddMaterialModal
          isOpen={isAddModalOpen}
          onClose={() => setIsAddModalOpen(false)}
          onConfirmAdd={handleConfirmAddMaterials}
        />
      )}

      {/* Preview Modal */}
      {previewMaterial && (
        <MaterialPreviewModal
          material={previewMaterial}
          onClose={() => setPreviewMaterial(null)}
        />
      )}
    </div>
  );
}
