import React, { useState } from 'react';
import MaterialDropzone from '../course/MaterialDropzone';
import SelectedMaterialList from '../course/SelectedMaterialList';

/**
 * AddMaterialModal
 * Modal allowing students to upload new course materials.
 * Reuses MaterialDropzone and SelectedMaterialList from Create Course.
 */
export default function AddMaterialModal({
  isOpen = false,
  onClose,
  onConfirmAdd,
}) {
  const [selectedMaterials, setSelectedMaterials] = useState([]);

  if (!isOpen) return null;

  const handleFilesSelected = (files) => {
    const formatted = files.map((file) => {
      const ext = file.name.split('.').pop().toLowerCase();
      let type = 'pdf';
      if (['ppt', 'pptx'].includes(ext)) type = 'ppt';
      else if (['mp4', 'mov', 'webm', 'm4v'].includes(ext)) type = 'video';

      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);

      return {
        id: `sel-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        name: file.name,
        type,
        sizeText: `${sizeMB} MB`,
        status: 'Ready',
        rawFile: file,
      };
    });

    setSelectedMaterials((prev) => [...prev, ...formatted]);
  };

  const handleRemoveMaterial = (id) => {
    setSelectedMaterials((prev) => prev.filter((m) => m.id !== id));
  };

  const handleConfirm = () => {
    if (selectedMaterials.length === 0) return;
    onConfirmAdd?.(selectedMaterials);
    setSelectedMaterials([]);
    onClose?.();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-2xl bg-[#0c0c0f] border border-[#27272a] rounded-xl shadow-2xl z-10 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="h-14 px-6 border-b border-[#27272a] flex items-center justify-between bg-[#0f0f12] shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[#a78bfa] text-xl">
              upload_file
            </span>
            <h3 className="text-base font-semibold text-white tracking-tight">
              Add Course Material
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <p className="text-sm text-[#a1a1aa] leading-relaxed">
            Upload textbooks, lecture slides, or recorded videos. Edvora will extract topics and ground your tutor and assessments.
          </p>

          {/* Reused Dropzone */}
          <MaterialDropzone onFilesSelected={handleFilesSelected} />

          {/* Reused Selected List */}
          <SelectedMaterialList
            materials={selectedMaterials}
            onRemoveMaterial={handleRemoveMaterial}
          />
        </div>

        {/* Footer */}
        <div className="p-4 px-6 border-t border-[#27272a] bg-[#0f0f12] flex items-center justify-between gap-3 shrink-0">
          <span className="text-xs text-[#71717a] font-mono">
            {selectedMaterials.length} file{selectedMaterials.length === 1 ? '' : 's'} selected
          </span>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-[#27272a] text-xs font-medium text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={selectedMaterials.length === 0}
              onClick={handleConfirm}
              className="px-5 py-2 rounded-lg bg-[#a78bfa] hover:bg-[#c4b5fd] text-[#0a0012] disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <span>Add to Course</span>
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

