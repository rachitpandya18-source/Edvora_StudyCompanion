export default function LandingPage({ onEnterWorkspace, onNavigateToAuth }) {
  const scrollToSection = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleSignIn = () => {
    if (onNavigateToAuth) {
      onNavigateToAuth('login');
    } else if (onEnterWorkspace) {
      onEnterWorkspace();
    }
  };

  const handleSignUp = () => {
    if (onNavigateToAuth) {
      onNavigateToAuth('signup');
    } else if (onEnterWorkspace) {
      onEnterWorkspace();
    }
  };

  return (
    <div className="bg-background text-on-surface antialiased min-h-screen flex flex-col selection:bg-primary/30 selection:text-on-surface">
      {/* 1. MINIMAL TOP NAVIGATION */}
      <header className="w-full sticky top-0 z-50 backdrop-blur-md bg-[#121316]/85 border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <a
            className="flex items-center gap-2.5 text-on-surface hover:text-white transition-colors"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          >
            <div className="w-7 h-7 rounded border border-white/15 bg-white/5 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[17px]">account_tree</span>
            </div>
            <span className="font-headline font-semibold text-lg tracking-tight">Edvora</span>
          </a>

          {/* Minimal Links & CTA */}
          <div className="flex items-center gap-6">
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="text-sm text-neutral-400 hover:text-white transition-colors hidden sm:inline-block cursor-pointer bg-transparent border-0 p-0"
            >
              How it works
            </button>
            <button
              onClick={handleSignIn}
              className="text-sm text-neutral-400 hover:text-white transition-colors cursor-pointer bg-transparent border-0 p-0"
            >
              Sign in
            </button>
            <button
              onClick={handleSignUp}
              className="inline-flex items-center justify-center px-4 py-1.5 text-sm font-medium rounded-lg bg-primary text-[#0a0012] hover:bg-primary-fixed-dim transition-colors cursor-pointer border-0"
            >
              Start learning
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* SECTION 1: HERO WITH LIVING COURSE MAP */}
        <section className="max-w-7xl mx-auto px-6 pt-16 sm:pt-20 pb-24 border-b border-white/10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
            {/* Editorial Left Column */}
            <div className="lg:col-span-6 flex flex-col items-start space-y-6">
              <h1 className="font-headline text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight text-white leading-[1.12]">
                Your syllabus isn&apos;t a pile of files. It&apos;s a learning system.
              </h1>
              <p className="text-lg sm:text-xl text-neutral-300 leading-relaxed max-w-xl">
                Edvora turns your lectures, slides and textbooks into a personal AI learning companion that understands your material, adapts to your progress, and helps you decide what to study next.
              </p>
              <div className="flex flex-wrap items-center gap-4 pt-2">
                <button
                  onClick={handleSignUp}
                  className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium rounded-lg bg-primary text-[#0a0012] hover:bg-primary-fixed-dim transition-colors cursor-pointer border-0"
                >
                  Start learning
                </button>
                <button
                  onClick={() => scrollToSection('how-it-works')}
                  className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-medium rounded-lg border border-white/10 bg-transparent text-neutral-300 hover:text-white hover:border-white/20 transition-colors cursor-pointer"
                >
                  See how it works
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </div>

            {/* Right Column: Living Course Map (Connected Conceptual Knowledge Graph) */}
            <div className="lg:col-span-6">
              <div className="rounded-xl border border-white/10 bg-[#16171b] p-6 sm:p-8 relative">
                {/* Header status row */}
                <div className="flex items-center justify-between pb-6 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span className="text-sm font-semibold text-white">CS 201: Data Structures &amp; Algorithms</span>
                  </div>
                  <span className="text-xs sm:text-sm text-neutral-400 font-mono">Term Progress · 68%</span>
                </div>

                {/* Authentic Graph View with SVG connectors & structural nodes */}
                <div className="relative pt-8 pb-4">
                  {/* SVG Connector Layer */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none stroke-white/15" fill="none" preserveAspectRatio="none">
                    {/* Arrays to Linked Lists horizontal connection */}
                    <line strokeDasharray="3 3" strokeWidth="1.5" x1="28%" x2="72%" y1="36" y2="36" />
                    {/* Linked Lists down to Trees and Graphs */}
                    <path d="M 72% 52 V 90 H 28% V 118" strokeWidth="1.5" />
                    <path d="M 72% 52 V 118" strokeDasharray="3 3" strokeWidth="1.5" />
                    {/* Trees down to AVL Trees */}
                    <line className="stroke-amber-400/40" strokeWidth="1.5" x1="28%" x2="28%" y1="158" y2="210" />
                    {/* AVL Trees anchor to Study Next */}
                    <line className="stroke-amber-400/30" strokeWidth="1.5" x1="28%" x2="28%" y1="268" y2="304" />
                  </svg>

                  {/* Node Row 1: Arrays & Linked Lists */}
                  <div className="grid grid-cols-2 gap-6 relative z-10 mb-10">
                    {/* Arrays Node */}
                    <div className="flex items-center justify-between p-3.5 rounded-lg border border-white/10 bg-[#121316]">
                      <div className="flex items-center gap-2.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span className="text-sm sm:text-base font-semibold text-white">Arrays</span>
                      </div>
                      <span className="text-xs sm:text-sm text-emerald-400 font-mono font-medium">94%</span>
                    </div>
                    {/* Linked Lists Node */}
                    <div className="flex items-center justify-between p-3.5 rounded-lg border border-white/10 bg-[#121316]">
                      <div className="flex items-center gap-2.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span className="text-sm sm:text-base font-semibold text-white">Linked Lists</span>
                      </div>
                      <span className="text-xs sm:text-sm text-emerald-400 font-mono font-medium">88%</span>
                    </div>
                  </div>

                  {/* Node Row 2: Trees & Graphs */}
                  <div className="grid grid-cols-2 gap-6 relative z-10 mb-10">
                    {/* Trees Node */}
                    <div className="flex items-center justify-between p-3.5 rounded-lg border border-purple-400/30 bg-[#121316]">
                      <div className="flex items-center gap-2.5">
                        <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                        <span className="text-sm sm:text-base font-semibold text-white">Trees</span>
                      </div>
                      <span className="text-xs sm:text-sm text-purple-300 font-mono font-medium">62%</span>
                    </div>
                    {/* Graphs Node (Locked) */}
                    <div className="flex items-center justify-between p-3.5 rounded-lg border border-dashed border-white/10 bg-[#121316]/50 opacity-60">
                      <div className="flex items-center gap-2.5">
                        <span className="w-2 h-2 rounded-full bg-neutral-500"></span>
                        <span className="text-sm sm:text-base font-semibold text-neutral-400">Graphs</span>
                      </div>
                      <span className="text-xs sm:text-sm text-neutral-500">Upcoming</span>
                    </div>
                  </div>

                  {/* Node Row 3: AVL Trees (Active Weak Node) */}
                  <div className="relative z-10 max-w-sm mb-5">
                    <div className="p-4 rounded-lg border border-amber-400/40 bg-[#121316] relative shadow-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                          <span className="text-sm sm:text-base font-semibold text-white">AVL Trees</span>
                        </div>
                        <span className="text-xs px-2.5 py-0.5 rounded border border-amber-500/30 bg-amber-500/10 text-amber-300 font-medium">
                          Needs attention · 43%
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-neutral-300">Balance factor violations &amp; dual-pivot rotations</p>
                    </div>
                  </div>

                  {/* Directly Connected / Anchored Study Next Box */}
                  <div className="relative z-10 ml-6 pl-4 border-l-2 border-amber-400/40">
                    <div className="p-3.5 rounded-lg border border-white/10 bg-[#1a1b20] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-start gap-2.5">
                        <span className="material-symbols-outlined text-primary text-[20px] mt-0.5">lightbulb</span>
                        <div>
                          <span className="text-xs sm:text-sm font-semibold text-white block">Study next</span>
                          <span className="text-xs sm:text-sm text-neutral-300">Review AVL rotations · Practice 3 questions</span>
                        </div>
                      </div>
                      <button
                        onClick={onEnterWorkspace}
                        className="inline-flex items-center gap-1 text-xs sm:text-sm font-semibold text-primary hover:text-primary-fixed-dim transition-colors self-start sm:self-center cursor-pointer bg-transparent border-0 p-0"
                      >
                        Begin
                        <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: MATERIAL → UNDERSTANDING → LEARNING LOOP */}
        <section className="max-w-7xl mx-auto px-6 py-24 border-b border-white/10" id="how-it-works">
          <div className="max-w-3xl mb-16">
            <h2 className="font-headline text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight text-white mb-4">
              From raw course files to an integrated mental model.
            </h2>
            <p className="text-lg text-neutral-300 leading-relaxed">
              No more switching between 400-page PDFs, lecture slide decks, and hour-long lecture videos.
            </p>
          </div>

          {/* Ingest Sources Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
            <div className="flex items-center gap-3 p-4 rounded-lg border border-white/10 bg-[#16171b]">
              <span className="material-symbols-outlined text-primary text-[20px]">menu_book</span>
              <div>
                <div className="text-sm font-medium text-white">Textbook &amp; Syllabus</div>
                <div className="text-xs text-neutral-400">Algorithms_4thEd.pdf</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 rounded-lg border border-white/10 bg-[#16171b]">
              <span className="material-symbols-outlined text-emerald-400 text-[20px]">co_present</span>
              <div>
                <div className="text-sm font-medium text-white">Lecture Slides</div>
                <div className="text-xs text-neutral-400">Lecture_05_AVL_Trees.pptx</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 rounded-lg border border-white/10 bg-[#16171b]">
              <span className="material-symbols-outlined text-amber-400 text-[20px]">videocam</span>
              <div>
                <div className="text-sm font-medium text-white">Recorded Lectures</div>
                <div className="text-xs text-neutral-400">Lecture 05 · Timestamped Audio</div>
              </div>
            </div>
          </div>

          {/* Flow Connector */}
          <div className="flex items-center justify-center my-6">
            <div className="h-8 w-px bg-white/15"></div>
          </div>

          {/* Central Convergence Label */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/10 bg-[#16171b] text-xs font-medium text-neutral-300">
              <span className="w-2 h-2 rounded-full bg-primary"></span>
              <span className="text-xs sm:text-sm font-medium text-neutral-200">Synthesized into Edvora</span>
            </div>
          </div>

          {/* Editorial Learning Progression */}
          <div className="border-t border-b border-white/10 py-8">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-6 text-center">
              <div className="space-y-1">
                <span className="text-sm font-mono text-neutral-400">01</span>
                <div className="text-base font-semibold text-white">Understand</div>
                <p className="text-xs sm:text-sm text-neutral-400">Synthesizes texts and slides into one coherent model</p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-mono text-neutral-400">02</span>
                <div className="text-base font-semibold text-white">Ask</div>
                <p className="text-xs sm:text-sm text-neutral-400">Instant answers with exact citations into your materials</p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-mono text-primary">03</span>
                <div className="text-base font-semibold text-primary">Practice</div>
                <p className="text-xs sm:text-sm text-neutral-400">Targeted questions calibrated to detected weak points</p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-mono text-neutral-400">04</span>
                <div className="text-base font-semibold text-white">Master</div>
                <p className="text-xs sm:text-sm text-neutral-400">Concept retention tracked continuously over the term</p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-mono text-emerald-400">05</span>
                <div className="text-base font-semibold text-emerald-400">Study Next</div>
                <p className="text-xs sm:text-sm text-neutral-400">Continuous daily recommendations for high-leverage review</p>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 3: SOURCE-GROUNDED TUTOR */}
        <section className="max-w-7xl mx-auto px-6 py-24 border-b border-white/10">
          <div className="max-w-3xl mb-16">
            <h2 className="font-headline text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight text-white mb-4">
              Every answer can take you back to where it came from.
            </h2>
            <p className="text-lg text-neutral-300 leading-relaxed">
              Grounded in your course material. No made-up explanations, no guessing.
            </p>
          </div>

          {/* Clean Academic Split Pane */}
          <div className="rounded-xl border border-white/10 bg-[#16171b] overflow-hidden grid grid-cols-1 lg:grid-cols-12">
            {/* Left: Tutor Inquiry & Explanation */}
            <div className="lg:col-span-6 p-6 sm:p-8 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-white/10">
              <div className="space-y-6">
                {/* Student Prompt */}
                <div>
                  <span className="text-xs sm:text-sm text-neutral-400 block mb-2 font-medium">Student question</span>
                  <div className="p-4 rounded-lg border border-white/10 bg-[#121316] text-base sm:text-lg text-white font-medium leading-snug">
                    Why does an AVL tree need a rotation here?
                  </div>
                </div>

                {/* Explanation */}
                <div className="space-y-3">
                  <span className="text-sm text-primary font-semibold block">Edvora</span>
                  <div className="text-sm sm:text-base text-neutral-300 leading-relaxed space-y-3">
                    <p>
                      An AVL tree requires a rotation when the balance factor of any node exceeds the allowed threshold of{' '}
                      <span className="font-mono text-xs sm:text-sm px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-white">
                        {`{-1, 0, +1}`}
                      </span>.
                    </p>
                    <p>
                      In your case, inserting node <strong className="text-white font-semibold">28</strong> into the right subtree of node{' '}
                      <strong className="text-white font-semibold">25</strong> creates a Right-Left imbalance at node{' '}
                      <strong className="text-white font-semibold">20</strong>. A double rotation restores the height invariant without violating binary search ordering.
                    </p>
                  </div>
                </div>

                {/* Direct Citation Badges */}
                <div className="pt-4 border-t border-white/10">
                  <span className="text-xs sm:text-sm text-neutral-400 block mb-2.5 font-medium">Source references</span>
                  <div className="flex flex-wrap gap-2.5">
                    <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-primary/40 bg-primary/10 text-xs sm:text-sm text-white hover:bg-primary/20 transition-colors cursor-pointer">
                      <span className="text-primary font-medium">Trees.pdf</span> · <span className="font-mono">Page 42</span>
                      <span className="material-symbols-outlined text-[16px] text-primary">visibility</span>
                    </button>
                    <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-white/10 bg-[#121316] text-xs sm:text-sm text-neutral-300 hover:text-white hover:border-white/20 transition-colors cursor-pointer">
                      <span className="text-emerald-400 font-medium">Trees.pptx</span> · <span className="font-mono">Slide 18</span>
                    </button>
                    <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-white/10 bg-[#121316] text-xs sm:text-sm text-neutral-300 hover:text-white hover:border-white/20 transition-colors cursor-pointer">
                      <span className="text-amber-400 font-medium">Lecture 05</span> · <span className="font-mono">14:23</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Source Inspector Preview */}
            <div className="lg:col-span-6 p-6 sm:p-8 bg-[#121316] flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-white/10 text-xs text-neutral-400">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px] text-primary">description</span>
                    <span className="font-medium text-white">Trees.pdf · Page 42 (Section 4.3.2)</span>
                  </div>
                  <span className="font-mono">Page 42</span>
                </div>

                {/* Page Excerpt with Highlight */}
                <div className="p-4 rounded-lg border border-white/10 bg-[#16171b] space-y-4">
                  <div className="text-sm text-neutral-200 leading-relaxed">
                    An AVL tree is a self-balancing binary search tree. In an AVL tree, the{' '}
                    <span className="px-1.5 py-0.5 rounded bg-primary/20 text-white border border-primary/40 font-medium">
                      height of left and right subtrees may differ by at most 1. Upon violation, a left-right or right-left rotation is applied
                    </span>{' '}
                    to rebalance the node locally while preserving the global binary search property.
                  </div>

                  {/* Tree Diagram Snippet */}
                  <div className="p-4 rounded border border-white/10 bg-[#121316]">
                    <div className="text-xs text-neutral-400 mb-3">Figure 4.8 · Right-Left Double Rotation</div>
                    <div className="grid grid-cols-2 gap-4 text-center">
                      <div className="p-3 border border-dashed border-white/10 rounded">
                        <span className="text-xs text-neutral-400 block mb-2">Before Rotation</span>
                        <div className="font-mono text-xs sm:text-sm text-neutral-300 space-y-0.5">
                          <div className="text-amber-400 font-semibold">(20) [BF = -2]</div>
                          <div className="text-neutral-500 text-xs">↘</div>
                          <div>(25)</div>
                          <div className="text-neutral-500 text-xs">↙</div>
                          <div className="text-primary font-medium">(28)</div>
                        </div>
                      </div>
                      <div className="p-3 border border-white/10 rounded bg-white/5">
                        <span className="text-xs text-emerald-400 block mb-2">After Rotation</span>
                        <div className="font-mono text-xs sm:text-sm text-neutral-300 space-y-0.5">
                          <div className="text-emerald-400 font-semibold">(25) [BF = 0]</div>
                          <div className="text-neutral-500 text-xs">↙ &nbsp;&nbsp; ↘</div>
                          <div className="flex justify-around">
                            <span>(20)</span>
                            <span>(28)</span>
                          </div>
                          <div className="text-emerald-400 text-xs mt-1">Balanced</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Lecture Timestamp Link */}
                <div className="flex items-center justify-between text-xs sm:text-sm text-neutral-400 pt-1">
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-amber-400">schedule</span>
                    Referenced in Lecture 05 at <span className="font-mono text-white">14:23</span>
                  </span>
                  <a className="text-primary font-medium hover:text-primary-fixed-dim" href="#lecture" onClick={(e) => e.preventDefault()}>
                    View clip →
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 4: ADAPTIVE GUIDANCE / "STUDY NEXT" */}
        <section className="max-w-7xl mx-auto px-6 py-24 border-b border-white/10" id="study-next">
          <div className="max-w-3xl mb-14">
            <h2 className="font-headline text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight text-white mb-4">
              The system doesn&apos;t stop after answering. It guides what you study next.
            </h2>
            <p className="text-lg text-neutral-300 leading-relaxed">
              Edvora doesn&apos;t just tell you your score. It tells you what to do next.
            </p>
          </div>

          {/* Diagnostic Card */}
          <div className="rounded-xl border border-white/10 bg-[#16171b] p-6 sm:p-8 max-w-3xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/10">
              <div>
                <h3 className="font-headline text-xl sm:text-2xl font-semibold text-white">AVL Trees &amp; Self-Balancing Invariants</h3>
                <p className="text-xs sm:text-sm text-neutral-400 mt-1 font-mono">CS 201 · Topic Diagnostic</p>
              </div>
              <span className="inline-flex items-center gap-1.5 text-xs sm:text-sm px-3 py-1 rounded border border-amber-500/30 bg-amber-500/10 text-amber-300 font-medium self-start sm:self-auto">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span> 43% mastery · Needs attention
              </span>
            </div>

            {/* Retention bar */}
            <div className="py-5 border-b border-white/10">
              <div className="flex justify-between text-xs sm:text-sm text-neutral-300 mb-2 font-medium">
                <span>Current Retention</span>
                <span>Target: 85% for Exam Readiness</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full bg-amber-400 rounded-full" style={{ width: '43%' }}></div>
              </div>
            </div>

            {/* 3 Numbered Action Steps */}
            <div className="py-6 space-y-3">
              <div className="flex items-center gap-3 p-3.5 rounded-lg border border-white/10 bg-[#121316]">
                <span className="w-7 h-7 rounded-full border border-white/10 text-xs sm:text-sm font-mono flex items-center justify-center text-neutral-300">1</span>
                <div className="flex-1 text-sm">
                  <span className="text-white font-medium">Review AVL rotations</span>
                  <span className="text-neutral-400 ml-2 text-xs sm:text-sm">synthesized note from Trees.pdf</span>
                </div>
                <span className="material-symbols-outlined text-[18px] text-neutral-500">chevron_right</span>
              </div>

              <div className="flex items-center gap-3 p-3.5 rounded-lg border border-white/10 bg-[#121316]">
                <span className="w-7 h-7 rounded-full border border-white/10 text-xs sm:text-sm font-mono flex items-center justify-center text-neutral-300">2</span>
                <div className="flex-1 text-sm">
                  <span className="text-white font-medium">Watch Lecture 05 · <span className="font-mono">14:23</span></span>
                  <span className="text-neutral-400 ml-2 text-xs sm:text-sm">direct timestamp jump</span>
                </div>
                <span className="material-symbols-outlined text-[18px] text-neutral-500">chevron_right</span>
              </div>

              <div className="flex items-center gap-3 p-3.5 rounded-lg border border-primary/40 bg-[#121316]">
                <span className="w-7 h-7 rounded-full border border-primary text-xs sm:text-sm font-mono flex items-center justify-center text-primary font-semibold">3</span>
                <div className="flex-1 text-sm">
                  <span className="text-white font-medium">Practice 3 targeted questions</span>
                  <span className="text-neutral-400 ml-2 text-xs sm:text-sm">calibrated quiz</span>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">play_arrow</span>
              </div>
            </div>

            <div className="pt-3 flex justify-end">
              <button
                onClick={onEnterWorkspace}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-[#0a0012] font-semibold text-sm hover:bg-primary-fixed-dim transition-colors cursor-pointer border-0"
              >
                <span>Start AVL Practice (3 min)</span>
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </button>
            </div>
          </div>
        </section>

        {/* SECTION 5: MINIMAL FINAL CTA */}
        <section className="max-w-7xl mx-auto px-6 py-28 text-center">
          <div className="max-w-2xl mx-auto space-y-6">
            <h2 className="font-headline text-4xl sm:text-5xl font-semibold tracking-tight text-white">
              Start learning with your own course material.
            </h2>
            <div>
              <button
                onClick={handleSignUp}
                className="inline-flex items-center justify-center px-7 py-3.5 text-base font-semibold rounded-lg bg-primary text-[#0a0012] hover:bg-primary-fixed-dim transition-colors cursor-pointer border-0"
              >
                Create your learning space
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* MINIMAL FOOTER */}
      <footer className="w-full border-t border-white/10 bg-[#121316]">
        <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded border border-white/15 bg-white/5 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[13px]">account_tree</span>
            </div>
            <span className="font-headline text-sm font-medium text-white">Edvora</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-neutral-400">
            <a className="hover:text-white transition-colors" href="#product" onClick={(e) => e.preventDefault()}>Product</a>
            <a className="hover:text-white transition-colors" href="#privacy" onClick={(e) => e.preventDefault()}>Privacy</a>
            <a className="hover:text-white transition-colors" href="#terms" onClick={(e) => e.preventDefault()}>Terms</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
