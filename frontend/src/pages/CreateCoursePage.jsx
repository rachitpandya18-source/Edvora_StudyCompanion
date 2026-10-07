import { useState } from 'react';
import AppLayout from '../components/layout/AppLayout';
import MaterialDropzone from '../components/course/MaterialDropzone';
import SelectedMaterialList from '../components/course/SelectedMaterialList';
import { mockStudentProfile, mockCourses } from '../data/mockDashboardData';

const INITIAL_MATERIALS = [
  {
    id: 'mat-1',
    name: 'Algorithms_and_Data_Structures_4thEd.pdf',
    type: 'pdf',
    sizeText: 'PDF · 48 pages · 14.2 MB',
    status: 'Ready',
  },
  {
    id: 'mat-2',
    name: 'Lecture_05_AVL_Trees.pptx',
    type: 'pptx',
    sizeText: 'PPTX · 32 slides · 8.4 MB',
    status: 'Ready',
  },
  {
    id: 'mat-3',
    name: 'Lecture_05_Live_Recording.mp4',
    type: 'video',
    sizeText: 'Video · 52 min · 240 MB',
    status: 'Processing...',
  },
];

export default function CreateCoursePage({
  user = mockStudentProfile,
  recentCourses = mockCourses,
  onBackToDashboard,
  onCourseCreated,
}) {
  const [courseName, setCourseName] = useState('Data Structures & Algorithms');
  const [description, setDescription] = useState(
    'Core concepts of asymptotic complexity, trees, heaps, graphs, balanced search trees, and dynamic programming applications.'
  );
  const [materials, setMaterials] = useState(INITIAL_MATERIALS);
  const [nameError, setNameError] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  };

  const handleFilesSelected = (newFiles) => {
    const formatted = newFiles.map((file, idx) => {
      const ext = file.name.split('.').pop().toLowerCase();
      let type = 'file';
      if (['pdf'].includes(ext)) type = 'pdf';
      else if (['ppt', 'pptx'].includes(ext)) type = 'pptx';
      else if (['mp4', 'mov', 'webm', 'm4v'].includes(ext)) type = 'video';

      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      const sizeText = `${type.toUpperCase()} · ${sizeMb} MB`;

      return {
        id: `custom-mat-${Date.now()}-${idx}`,
        name: file.name,
        type,
        sizeText,
        status: 'Processing...',
      };
    });

    setMaterials((prev) => [...prev, ...formatted]);
    showToast(`Added ${formatted.length} file${formatted.length > 1 ? 's' : ''}`);

    // Simulate completion for processing files
    setTimeout(() => {
      setMaterials((prev) =>
        prev.map((m) =>
          formatted.some((f) => f.id === m.id) ? { ...m, status: 'Ready' } : m
        )
      );
    }, 1500);
  };

  const handleRemoveMaterial = (id) => {
    setMaterials((prev) => prev.filter((m) => m.id !== id));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = courseName.trim();

    if (!trimmed) {
      setNameError('Please enter a course name.');
      return;
    }

    setNameError('');
    setIsCreating(true);
    showToast('Creating course learning space...');

    setTimeout(() => {
      setIsCreating(false);
      if (onCourseCreated) {
        onCourseCreated({
          courseName: trimmed,
          description: description.trim(),
          materials,
        });
      }
    }, 900);
  };

  const handleSidebarNavigate = (navId) => {
    if (navId === 'home' && onBackToDashboard) {
      onBackToDashboard();
    }
  };

  return (
    <AppLayout
      activeNav="courses"
      user={user}
      recentCourses={recentCourses}
      onNavigate={handleSidebarNavigate}
    >
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto py-10 px-6 sm:px-10">
          {/* Toast feedback */}
          {toastMessage && (
            <div className="fixed bottom-6 right-6 z-50 p-3.5 rounded-xl bg-[#18181c] border border-primary/50 text-white text-sm font-medium shadow-2xl flex items-center gap-2.5 animate-fade-in">
              <span className="material-symbols-outlined text-[18px] text-primary">info</span>
              <span>{toastMessage}</span>
            </div>
          )}

          {/* Navigation Breadcrumb / Return Path */}
          <div>
            <button
              type="button"
              onClick={onBackToDashboard}
              className="inline-flex items-center gap-2 text-sm font-medium text-[#a1a1aa] hover:text-primary transition-colors group cursor-pointer bg-transparent border-0 p-0"
            >
              <span className="material-symbols-outlined text-[18px] transition-transform group-hover:-translate-x-0.5">
                arrow_back
              </span>
              <span>Back to Dashboard</span>
            </button>
          </div>

          {/* Page Header */}
          <header className="mt-6 mb-8">
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-white font-headline">
              Create a new course
            </h1>
            <p className="text-base sm:text-lg text-[#a1a1aa] mt-2 font-normal">
              Build a learning space around your own course material.
            </p>
          </header>

          {/* Form Container */}
          <form onSubmit={handleSubmit} className="space-y-6" id="create-course-form">
            {/* Section 1: Course Details */}
            <section className="rounded-2xl border border-[#27272a] bg-[#121215]/80 p-6 sm:p-8 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl sm:text-[28px] font-semibold tracking-tight text-white font-headline">
                  Course details
                </h2>
              </div>

              <div className="space-y-5">
                {/* Field 1: Course Name (Required) */}
                <div>
                  <label
                    className="block text-sm sm:text-base font-medium text-white mb-2"
                    htmlFor="course-name"
                  >
                    Course name <span className="text-primary">*</span>
                  </label>
                  <input
                    id="course-name"
                    type="text"
                    required
                    value={courseName}
                    onChange={(e) => {
                      setCourseName(e.target.value);
                      if (nameError) setNameError('');
                    }}
                    placeholder="e.g. Data Structures & Algorithms"
                    className={`w-full text-base bg-[#09090b] border rounded-xl px-4 py-3.5 text-white placeholder:text-[#71717a] outline-none transition-colors ${
                      nameError
                        ? 'border-red-500/80 focus:border-red-500 focus:ring-1 focus:ring-red-500'
                        : 'border-[#27272a] focus:border-primary focus:ring-1 focus:ring-primary'
                    }`}
                  />
                  {nameError ? (
                    <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1 font-medium">
                      <span className="material-symbols-outlined text-[14px]">error</span>
                      {nameError}
                    </p>
                  ) : (
                    <p className="text-xs text-[#a1a1aa] mt-1.5">
                      Choose a name you&apos;ll recognize later.
                    </p>
                  )}
                </div>

                {/* Field 2: Description (Optional) */}
                <div>
                  <label
                    className="block text-sm sm:text-base font-medium text-white mb-2"
                    htmlFor="course-desc"
                  >
                    Description
                  </label>
                  <textarea
                    id="course-desc"
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What are you studying in this course?"
                    className="w-full text-base bg-[#09090b] border border-[#27272a] focus:border-primary focus:ring-1 focus:ring-primary rounded-xl px-4 py-3 text-white placeholder:text-[#71717a] outline-none transition-colors resize-none"
                  />
                </div>
              </div>
            </section>

            {/* Section 2: Learning Material */}
            <section className="rounded-2xl border border-[#27272a] bg-[#121215]/80 p-6 sm:p-8 backdrop-blur-sm">
              <div className="mb-6">
                <h2 className="text-2xl sm:text-[28px] font-semibold tracking-tight text-white font-headline">
                  Add your learning material
                </h2>
                <p className="text-sm sm:text-base text-[#a1a1aa] mt-1">
                  Bring the textbooks, slides and lectures you already study from.
                </p>
              </div>

              {/* Drag & Drop Upload Zone */}
              <MaterialDropzone onFilesSelected={handleFilesSelected} />

              {/* Uploaded Materials List */}
              <SelectedMaterialList
                materials={materials}
                onRemoveMaterial={handleRemoveMaterial}
              />
            </section>

            {/* Bottom Action Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-[#27272a]">
              <div className="flex items-center gap-2 text-sm text-[#a1a1aa]">
                <span className="material-symbols-outlined text-primary text-[18px]">
                  auto_awesome
                </span>
                <span>Your tutor will learn from these materials.</span>
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  onClick={onBackToDashboard}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-[#27272a] text-[15px] sm:text-base font-medium text-[#a1a1aa] hover:text-white hover:bg-[#18181c] transition-colors cursor-pointer bg-transparent"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={isCreating || !courseName.trim()}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-primary text-[#0a0012] font-semibold text-[15px] sm:text-base hover:opacity-95 active:scale-[0.99] transition-all shadow-sm cursor-pointer border-0 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? (
                    <>
                      <span className="w-4 h-4 border-2 border-[#0a0012] border-t-transparent rounded-full animate-spin" />
                      <span>Creating Course...</span>
                    </>
                  ) : (
                    <>
                      <span>Create Course</span>
                      <span className="material-symbols-outlined text-[18px]">
                        arrow_forward
                      </span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}

