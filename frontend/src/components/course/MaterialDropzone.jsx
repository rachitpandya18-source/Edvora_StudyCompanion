import { useState, useRef } from 'react';

export default function MaterialDropzone({ onFilesSelected }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      if (onFilesSelected) {
        onFilesSelected(Array.from(e.dataTransfer.files));
      }
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      if (onFilesSelected) {
        onFilesSelected(Array.from(e.target.files));
      }
      e.target.value = ''; // Reset so the same file can be selected again if needed
    }
  };

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      className={`relative group rounded-2xl border-2 border-dashed transition-all duration-200 p-8 sm:p-10 text-center cursor-pointer ${
        isDragOver
          ? 'border-primary bg-[#18181b]/70'
          : 'border-[#52525b] hover:border-primary/80 bg-[#09090b]/60 hover:bg-[#09090b]/90'
      }`}
    >
      <input
        ref={fileInputRef}
        aria-label="Upload study files"
        className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10"
        multiple
        type="file"
        accept=".pdf,.ppt,.pptx,.mp4,.mov,.m4v,.webm"
        onChange={handleFileInputChange}
      />

      <div className="flex flex-col items-center justify-center pointer-events-none">
        <div className="w-14 h-14 rounded-2xl bg-[#18181b] border border-[#27272a] flex items-center justify-center text-primary group-hover:scale-105 group-hover:border-primary/50 transition-all duration-200 shadow-inner">
          <span className="material-symbols-outlined text-[28px]">cloud_upload</span>
        </div>

        <div className="mt-4">
          <p className="text-base sm:text-lg font-medium text-white">
            Drop your files here
          </p>
          <p className="text-sm text-primary font-medium mt-1">
            or browse your computer
          </p>
        </div>

        {/* Format pills */}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs text-[#a1a1aa] font-mono">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#121215] border border-[#27272a] text-[13px]">
            <span className="material-symbols-outlined text-[16px] text-[#a1a1aa]">description</span>
            PDF documents
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#121215] border border-[#27272a] text-[13px]">
            <span className="material-symbols-outlined text-[16px] text-[#a1a1aa]">slideshow</span>
            Slides (PPT, PPTX)
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#121215] border border-[#27272a] text-[13px]">
            <span className="material-symbols-outlined text-[16px] text-[#a1a1aa]">videocam</span>
            Videos (MP4, MOV)
          </span>
        </div>
      </div>
    </div>
  );
}

