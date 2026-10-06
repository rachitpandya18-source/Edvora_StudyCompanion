import { useState, useEffect } from 'react';
import Sidebar from './Sidebar';

export default function AppLayout({
  children,
  activeNav = 'home',
  onNavigate,
  user,
  recentCourses = [],
}) {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('edvora_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem('edvora_sidebar_collapsed', String(collapsed));
    } catch {
      // Ignore localStorage errors in sandbox/private mode
    }
  }, [collapsed]);

  const toggleCollapse = () => {
    setCollapsed((prev) => !prev);
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-[#f4f4f5] flex flex-col md:flex-row antialiased selection:bg-primary/30 selection:text-white">
      {/* Persistent Global Sidebar */}
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={toggleCollapse}
        activeNav={activeNav}
        onNavigate={onNavigate}
        user={user}
        recentCourses={recentCourses}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div
        className={`flex-1 min-w-0 flex flex-col min-h-screen transition-all duration-200 ${
          collapsed ? 'md:ml-20' : 'md:ml-64'
        }`}
      >
        {/* Mobile Header Bar */}
        <header className="md:hidden sticky top-0 z-20 bg-[#09090b]/90 backdrop-blur-md border-b border-[#222227] px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#18181c] cursor-pointer"
              aria-label="Open navigation menu"
            >
              <span className="material-symbols-outlined text-[22px]">menu</span>
            </button>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-[#18181c] border border-[#2e2e36] flex items-center justify-center text-[#a78bfa]">
                <span className="material-symbols-outlined text-[15px]">school</span>
              </div>
              <span className="font-bold text-sm tracking-tight text-white">EDVORA</span>
            </div>
          </div>

          <div className="w-7 h-7 rounded-full bg-[#202026] text-[#a78bfa] border border-[#2e2e36] flex items-center justify-center font-mono text-[11px]">
            {user?.initials || 'AR'}
          </div>
        </header>

        {/* Dynamic Page Content */}
        <main className="flex-1 min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}

