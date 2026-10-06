export default function Sidebar({
  collapsed = false,
  onToggleCollapse,
  activeNav = 'home',
  onNavigate,
  user,
  recentCourses = [],
  mobileOpen = false,
  onCloseMobile,
}) {
  const userName = user?.name || 'Alex Rivera';
  const userInitials = user?.initials || (userName.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase() || 'AR');
  const userProgram = user?.program || 'Computer Science';

  const handleNavClick = (navId, extraData) => {
    if (onNavigate) {
      onNavigate(navId, extraData);
    }
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden transition-opacity"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      {/* Main Sidebar Element */}
      <aside
        id="sidebar"
        className={`fixed inset-y-0 left-0 z-50 md:z-30 bg-[#09090b] border-r border-[#222227] flex flex-col justify-between shrink-0 select-none transition-all duration-200 ${
          collapsed ? 'w-20' : 'w-64'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className={`p-5 ${collapsed ? 'px-3' : 'px-5'}`}>
          {/* Header Brand & Collapse Toggle */}
          <div className="flex items-center justify-between mb-8">
            <button
              type="button"
              onClick={() => handleNavClick('home')}
              className="flex items-center gap-2.5 group cursor-pointer overflow-hidden bg-transparent border-0 p-0 text-left"
              title="Edvora Home"
            >
              <div className="w-8 h-8 rounded-lg bg-[#18181c] border border-[#2e2e36] flex items-center justify-center text-[#a78bfa] group-hover:border-[#a78bfa] transition-colors shrink-0">
                <span className="material-symbols-outlined text-[19px]">school</span>
              </div>
              {!collapsed && (
                <div className="truncate">
                  <span className="font-bold text-base tracking-tight text-white block leading-none">
                    EDVORA
                  </span>
                  <span className="text-[11px] font-mono text-[#71717a] uppercase tracking-wider block mt-1">
                    ACADEMIC WORKSPACE
                  </span>
                </div>
              )}
            </button>

            {/* Collapse / Expand Toggle Button (Desktop) */}
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              className="hidden md:flex w-7 h-7 rounded-md text-[#71717a] hover:text-white hover:bg-[#18181c] border border-transparent hover:border-[#2e2e36] items-center justify-center transition-colors cursor-pointer shrink-0"
              title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              <span className="material-symbols-outlined text-[18px]">
                {collapsed ? 'dock_to_right' : 'dock_to_left'}
              </span>
            </button>

            {/* Close Button on Mobile */}
            <button
              type="button"
              onClick={onCloseMobile}
              className="md:hidden w-7 h-7 rounded-md text-[#71717a] hover:text-white flex items-center justify-center cursor-pointer"
              aria-label="Close menu"
            >
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>

          {/* Global Navigation */}
          <nav className="space-y-1.5" aria-label="Sidebar Navigation">
            {/* Home */}
            <button
              type="button"
              onClick={() => handleNavClick('home')}
              title="Home"
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[15px] font-medium transition-colors cursor-pointer border-0 ${
                collapsed ? 'justify-center px-2' : ''
              } ${
                activeNav === 'home'
                  ? 'text-white bg-[#18181c] border border-[#2e2e36]/60 shadow-sm'
                  : 'text-[#a1a1aa] hover:text-white hover:bg-[#18181c] bg-transparent'
              }`}
            >
              <span className={`material-symbols-outlined text-[20px] ${activeNav === 'home' ? 'text-[#a78bfa]' : 'text-[#71717a]'}`}>
                home
              </span>
              {!collapsed && <span>Home</span>}
            </button>

            {/* My Courses */}
            <button
              type="button"
              onClick={() => handleNavClick('courses')}
              title="My Courses"
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-[15px] font-medium transition-colors cursor-pointer border-0 ${
                collapsed ? 'justify-center px-2' : ''
              } ${
                activeNav === 'courses'
                  ? 'text-white bg-[#18181c] border border-[#2e2e36]/60 shadow-sm'
                  : 'text-[#a1a1aa] hover:text-white hover:bg-[#18181c] bg-transparent'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={`material-symbols-outlined text-[20px] ${activeNav === 'courses' ? 'text-[#a78bfa]' : 'text-[#71717a]'}`}>
                  folder_open
                </span>
                {!collapsed && <span>My Courses</span>}
              </div>
              {!collapsed && (
                <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-[#222227] text-[#a1a1aa]">
                  {recentCourses.length || 3}
                </span>
              )}
            </button>
          </nav>

          {/* Recent Courses Section */}
          <div className="mt-8 pt-6 border-t border-[#222227]">
            {!collapsed ? (
              <>
                <span className="text-xs font-mono uppercase tracking-wider text-[#71717a] px-3 block mb-3 font-medium">
                  Recent Courses
                </span>
                <div className="space-y-1">
                  {recentCourses.map((course) => (
                    <button
                      key={course.id}
                      type="button"
                      onClick={() => handleNavClick('workspace', { courseId: course.id })}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-[14px] text-[#a1a1aa] hover:text-white hover:bg-[#18181c] transition-colors group cursor-pointer bg-transparent border-0"
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <span
                          className="w-1.5 h-1.5 rounded-full shrink-0"
                          style={{ backgroundColor: course.statusColor || '#fbbf24' }}
                        />
                        <span className="truncate group-hover:text-white font-medium">
                          {course.title}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-[#71717a] shrink-0 ml-2">
                        {course.mastery}%
                      </span>
                    </button>
                  ))}
                </div>
              </>
            ) : (
              /* Collapsed course dots rail */
              <div className="flex flex-col items-center gap-2.5 py-1">
                {recentCourses.map((course) => (
                  <button
                    key={course.id}
                    type="button"
                    onClick={() => handleNavClick('workspace', { courseId: course.id })}
                    title={`${course.title} (${course.mastery}%)`}
                    className="w-8 h-8 rounded-lg bg-[#18181c] border border-[#2e2e36] hover:border-white/40 flex items-center justify-center transition-colors cursor-pointer"
                  >
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: course.statusColor || '#fbbf24' }}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Bottom: Settings & Student Profile */}
        <div className={`p-4 border-t border-[#222227] space-y-2 ${collapsed ? 'px-2' : 'px-4'}`}>
          <button
            type="button"
            onClick={() => handleNavClick('settings')}
            title="Settings"
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[14px] text-[#a1a1aa] hover:text-white hover:bg-[#18181c] transition-colors cursor-pointer bg-transparent border-0 ${
              collapsed ? 'justify-center px-1' : ''
            }`}
          >
            <span className="material-symbols-outlined text-[19px] text-[#71717a]">settings</span>
            {!collapsed && <span>Settings</span>}
          </button>

          {/* User Profile Card */}
          {!collapsed ? (
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#121215] border border-[#222227]">
              <div className="relative shrink-0">
                <div className="w-8 h-8 rounded-full bg-[#202026] text-[#a78bfa] border border-[#2e2e36] flex items-center justify-center font-mono font-medium text-xs">
                  {userInitials}
                </div>
                <span className="absolute bottom-0 right-0 w-2 h-2 rounded-full bg-[#34d399] ring-2 ring-[#121215]" />
              </div>
              <div className="truncate leading-tight">
                <p className="text-[14px] font-medium text-white truncate">{userName}</p>
                <p className="text-[12px] font-mono text-[#71717a] truncate mt-0.5">{userProgram}</p>
              </div>
            </div>
          ) : (
            <div
              className="flex justify-center py-1"
              title={`${userName} · ${userProgram}`}
            >
              <div className="relative">
                <div className="w-8 h-8 rounded-full bg-[#202026] text-[#a78bfa] border border-[#2e2e36] flex items-center justify-center font-mono font-medium text-xs">
                  {userInitials}
                </div>
                <span className="absolute bottom-0 right-0 w-2 h-2 rounded-full bg-[#34d399] ring-2 ring-[#121215]" />
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

