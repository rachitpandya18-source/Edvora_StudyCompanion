import React, { useState, useEffect, useRef } from 'react';
import Citation from './Citation';
import SourcePanel from './SourcePanel';
import OutsideMaterialNotice from './OutsideMaterialNotice';
import FollowUpActions from './FollowUpActions';
import TutorComposer from './TutorComposer';
import {
  defaultTutorSources,
  initialTutorMessages,
  generalKnowledgeAnswer,
  courseOnlyAnswer,
} from '../../data/mockTutorData';

/**
 * CourseTutorView
 * Complete two-pane interactive workspace for the Edvora Course Tutor.
 */
export default function CourseTutorView({
  user,
  courseName = 'Data Structures & Algorithms',
}) {
  const [sources] = useState(defaultTutorSources);
  const [messages, setMessages] = useState(initialTutorMessages);
  const [activeSource, setActiveSource] = useState(2); // Default to Slide 18
  const [isSourcesOpen, setIsSourcesOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [boundaryChoice, setBoundaryChoice] = useState(null); // 'general' | 'course-only' | null
  const chatBottomRef = useRef(null);

  const userInitials =
    user?.initials ||
    (user?.name
      ? user.name
          .split(' ')
          .map((n) => n[0])
          .join('')
          .slice(0, 2)
          .toUpperCase()
      : 'AR');

  // Track screen size for mobile drawer vs desktop pane
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      if (mobile) {
        // Default to closed on small mobile viewports to prioritize conversation
        setIsSourcesOpen(false);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleSelectSource = (sourceNumber) => {
    setActiveSource(sourceNumber);
    if (!isSourcesOpen) {
      setIsSourcesOpen(true);
    }
  };

  const handleCitationClick = (citationNumber) => {
    setActiveSource(citationNumber);
    setIsSourcesOpen(true);
  };

  const handleSendMessage = (text) => {
    const studentMsg = {
      id: `msg-${Date.now()}`,
      sender: 'student',
      time: 'Just now',
      text,
    };

    // Simulated responsive Tutor answer
    const simulatedTutorMsg = {
      id: `msg-${Date.now() + 1}`,
      sender: 'tutor',
      time: 'Just now',
      isGrounded: true,
      lead: `Based on your course materials for ${courseName}, here is how this concept works:`,
      leadCitation: 1,
      stepsHeading: 'Key points from lecture slides:',
      steps: [
        {
          num: 1,
          title: 'Core invariant check',
          desc: 'Balance factor strictly maintained between -1, 0, and +1 after every insert or delete operation.',
          citation: 1,
        },
        {
          num: 2,
          title: 'Subtree height rebalancing',
          desc: 'Apply appropriate rotation vectors to preserve logarithmic height O(log n).',
          citation: 2,
        },
      ],
      sourcesSummary: [
        { type: 'PDF', num: 1, label: 'Trees.pdf · P.42', sourceId: 'source-1' },
        { type: 'PPT', num: 2, label: 'Lecture_05_AVL.pptx · Slide 18', sourceId: 'source-2' },
      ],
    };

    setMessages((prev) => [...prev, studentMsg, simulatedTutorMsg]);
    setTimeout(() => {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleFollowUpAction = (actionId, label) => {
    const studentFollowUp = {
      id: `fu-${Date.now()}`,
      sender: 'student',
      time: 'Just now',
      text: label,
    };

    let replyText = '';
    if (actionId === 'simpler') {
      replyText =
        'In simpler terms: A single rotation only fixes a straight line imbalance (like Left-Left). When the tree has a zigzag bend (Left-Right), you must first straighten the bend into a line, then rotate the whole branch down.';
    } else if (actionId === 'example') {
      replyText =
        'Example: Suppose we have nodes 20 and 10, then insert 15. Node 10 has right child 15 (a zigzag). We first left-rotate 10 and 15 so that 10 is the left child of 15. Now 20 -> 15 -> 10 is a straight line, and a right rotation on 20 puts 15 at the top with children 10 and 20!';
    } else if (actionId === 'stepbystep') {
      replyText =
        'Step 1: Identify imbalance: BF(Parent) = +2 and BF(Left Child) = -1.\nStep 2: Perform Left-Rotation on Left Child.\nStep 3: Update balance factors.\nStep 4: Perform Right-Rotation on Parent.\nStep 5: Verify tree height invariant restored.';
    } else {
      replyText =
        'Quick check: In an AVL tree with root node 30, left child 20, and node 25 just inserted: what rotation sequence is required to restore balance?';
    }

    const tutorFollowUp = {
      id: `fu-ans-${Date.now()}`,
      sender: 'tutor-followup',
      time: 'Just now',
      text: replyText,
    };

    setMessages((prev) => [...prev, studentFollowUp, tutorFollowUp]);
    setTimeout(() => {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleAnswerGenerally = () => {
    setBoundaryChoice('general');
    setTimeout(() => {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleStayCourseOnly = () => {
    setBoundaryChoice('course-only');
    setTimeout(() => {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  return (
    <div className="rounded-xl border border-[#27272a] bg-[#09090b] overflow-hidden flex flex-col h-[calc(100vh-210px)] min-h-[620px] shadow-2xl">
      {/* Two-Pane Workspace Canvas */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative">
        {/* ==================== LEFT PANE: CONVERSATION (~62% or 100%) ==================== */}
        <section
          className={`flex flex-col h-full bg-[#09090b] transition-all duration-200 ${
            isSourcesOpen && !isMobile
              ? 'w-[62%] border-r border-[#27272a]'
              : 'w-full'
          }`}
        >
          {/* Status Bar & Student Mastery Context */}
          <div className="px-6 py-3 border-b border-[#27272a] bg-[#0f0f12]/80 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#34d399] opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#34d399]" />
              </span>
              <span className="text-xs font-medium text-[#34d399] flex items-center gap-1">
                Course grounded · {sources.length} sources
              </span>
            </div>

            <div className="flex items-center gap-3">
              {/* Current focus badge */}
              <div className="flex items-center gap-2 text-xs text-[#a1a1aa] bg-[#121215] px-3 py-1 rounded border border-[#27272a]">
                <span className="material-symbols-outlined text-[#a78bfa] text-sm">
                  auto_awesome
                </span>
                <span className="text-xs text-[#fafafa] font-medium truncate">
                  Current focus: AVL Trees
                </span>
                <span className="text-[#a1a1aa]">·</span>
                <span className="text-xs font-mono font-semibold text-amber-300">
                  43% mastery
                </span>
              </div>

              {/* Toggle Sources button if collapsed */}
              {(!isSourcesOpen || isMobile) && (
                <button
                  type="button"
                  onClick={() => setIsSourcesOpen(true)}
                  className="px-2.5 py-1 rounded bg-[#18181c] border border-[#27272a] hover:border-[#a78bfa] text-xs font-medium text-[#a78bfa] hover:text-white transition-colors flex items-center gap-1.5 cursor-pointer"
                  title="View sources"
                >
                  <span className="material-symbols-outlined text-sm">menu_book</span>
                  <span>Sources ({sources.length})</span>
                </button>
              )}
            </div>
          </div>

          {/* Chat Stream (Scrollable) */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {messages.map((msg) => {
              // Student Message
              if (msg.sender === 'student') {
                return (
                  <div
                    key={msg.id}
                    className="flex items-start gap-3.5 max-w-3xl ml-auto justify-end"
                  >
                    <div className="bg-[#1e1e22] border border-[#27272a] rounded-2xl rounded-tr-sm p-4 text-sm text-[#fafafa] max-w-xl shadow-sm leading-relaxed">
                      <p className="font-normal text-[#fafafa]">{msg.text}</p>
                      {msg.reference && (
                        <div className="mt-2 pt-2 border-t border-[#27272a]/80 flex items-center justify-between text-[11px] text-[#a1a1aa]">
                          <span>
                            Referencing:{' '}
                            <span className="text-[#fafafa] font-mono">
                              {msg.reference}
                            </span>
                          </span>
                          <span>{msg.time}</span>
                        </div>
                      )}
                    </div>
                    <div className="w-8 h-8 rounded-full bg-[#18181b] border border-[#27272a] flex items-center justify-center text-xs font-semibold text-[#fafafa] shrink-0">
                      {userInitials}
                    </div>
                  </div>
                );
              }

              // Tutor Grounded Response 1
              if (msg.sender === 'tutor' && msg.isGrounded) {
                return (
                  <div key={msg.id} className="flex items-start gap-3.5 max-w-3xl">
                    <div className="w-8 h-8 rounded-full bg-[#a78bfa]/20 border border-[#a78bfa]/50 flex items-center justify-center text-[#a78bfa] shrink-0 mt-0.5">
                      <span className="material-symbols-outlined text-base">smart_toy</span>
                    </div>

                    <div className="flex-1 space-y-4">
                      {/* Main Answer Bubble */}
                      <div className="bg-[#121215] border border-[#27272a] rounded-2xl rounded-tl-sm p-5 space-y-4 text-[#fafafa] text-[15px] leading-relaxed shadow-sm">
                        <p className="text-[#fafafa] text-[15px] leading-relaxed">
                          {msg.lead}{' '}
                          {msg.leadCitation && (
                            <Citation
                              number={msg.leadCitation}
                              onClick={handleCitationClick}
                            />
                          )}
                          .
                        </p>

                        {/* Numbered Steps */}
                        {msg.steps && (
                          <div className="space-y-2 pt-1">
                            <div className="text-xs font-medium text-[#a1a1aa]">
                              {msg.stepsHeading || 'Resolution steps:'}
                            </div>
                            <div className="space-y-2 text-sm text-[#fafafa]">
                              {msg.steps.map((step) => (
                                <div
                                  key={step.num}
                                  className="flex items-start gap-2.5"
                                >
                                  <span className="shrink-0 w-5 h-5 rounded-full bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/40 flex items-center justify-center text-xs font-bold font-mono">
                                    {step.num}
                                  </span>
                                  <p className="leading-relaxed">
                                    <strong className="font-medium text-[#fafafa]">
                                      {step.title}
                                    </strong>{' '}
                                    {step.desc}{' '}
                                    {step.citation && (
                                      <Citation
                                        number={step.citation}
                                        onClick={handleCitationClick}
                                      />
                                    )}
                                    .
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Diagram Card Preview (Slide 18) */}
                        {msg.diagramPreview && (
                          <div
                            onClick={() => handleSelectSource(2)}
                            className="border border-[#27272a] rounded-lg p-3 bg-[#0c0c0f] hover:border-[#a78bfa]/50 transition-colors cursor-pointer"
                          >
                            <div className="flex items-center justify-between text-xs font-medium text-[#fafafa] pb-2 border-b border-[#27272a]">
                              <div className="flex items-center gap-2">
                                <span className="material-symbols-outlined text-[#a78bfa] text-base">
                                  image
                                </span>
                                <span>{msg.diagramPreview.title}</span>
                              </div>
                              <span className="text-[11px] text-[#a78bfa] font-mono">
                                {msg.diagramPreview.tag}
                              </span>
                            </div>

                            <div className="mt-2.5 flex items-center gap-3">
                              <div className="w-32 h-16 bg-[#18181b] rounded border border-[#27272a] flex flex-col items-center justify-center p-2 text-center shrink-0">
                                <div className="text-[10px] font-mono text-[#a78bfa] font-bold">
                                  {msg.diagramPreview.nodeRoot}
                                </div>
                                <div className="text-[9px] text-[#a1a1aa]">
                                  {msg.diagramPreview.nodeChild}
                                </div>
                                <div className="text-[9px] text-amber-400">
                                  {msg.diagramPreview.nodeSubtree}
                                </div>
                              </div>

                              <div className="text-xs text-[#a1a1aa] space-y-1">
                                <p className="text-xs text-[#fafafa]">
                                  {msg.diagramPreview.heightDiff}
                                </p>
                                <p className="text-[11px] text-[#71717a]">
                                  {msg.diagramPreview.instruction}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Sources Summary Row */}
                        {msg.sourcesSummary && (
                          <div className="pt-3 border-t border-[#27272a] flex flex-wrap items-center gap-2">
                            <span className="text-[11px] uppercase font-semibold text-[#a1a1aa] mr-1">
                              Sources:
                            </span>
                            {msg.sourcesSummary.map((s) => (
                              <button
                                key={s.num}
                                type="button"
                                onClick={() => handleCitationClick(s.num)}
                                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#18181b] border text-xs text-[#fafafa] transition-colors cursor-pointer ${
                                  activeSource === s.num
                                    ? 'border-[#a78bfa] text-white shadow-sm ring-1 ring-[#a78bfa]/30'
                                    : 'border-[#27272a] hover:border-[#a78bfa]'
                                }`}
                              >
                                <span
                                  className={`text-[10px] font-mono px-1 rounded border ${
                                    s.type === 'PDF'
                                      ? 'bg-red-500/20 text-red-300 border-red-500/30'
                                      : s.type === 'PPT'
                                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                                      : 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                                  }`}
                                >
                                  {s.type}
                                </span>
                                <span className="font-mono text-[11px] text-[#a78bfa]">
                                  [{s.num}]
                                </span>
                                <span className="text-xs truncate max-w-[150px]">
                                  {s.label}
                                </span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Follow-Up Action Chips */}
                      <FollowUpActions onSelectAction={handleFollowUpAction} />
                    </div>
                  </div>
                );
              }

              // Follow-up answer
              if (msg.sender === 'tutor-followup') {
                return (
                  <div key={msg.id} className="flex items-start gap-3.5 max-w-3xl">
                    <div className="w-8 h-8 rounded-full bg-[#a78bfa]/20 border border-[#a78bfa]/50 flex items-center justify-center text-[#a78bfa] shrink-0 mt-0.5">
                      <span className="material-symbols-outlined text-base">lightbulb</span>
                    </div>
                    <div className="bg-[#121215] border border-[#27272a] rounded-2xl rounded-tl-sm p-4 text-sm text-[#fafafa] max-w-xl leading-relaxed whitespace-pre-line">
                      {msg.text}
                    </div>
                  </div>
                );
              }

              // Outside Course Material Notice
              if (msg.sender === 'tutor-boundary') {
                return (
                  <div key={msg.id} className="pt-2 border-t border-[#27272a]/60 space-y-4">
                    <OutsideMaterialNotice
                      courseName={courseName}
                      onAnswerGenerally={handleAnswerGenerally}
                      onStayCourseOnly={handleStayCourseOnly}
                    />

                    {/* Render choice result if selected */}
                    {boundaryChoice === 'general' && (
                      <div className="flex items-start gap-3.5 max-w-3xl pl-11">
                        <div className="bg-[#121215] border border-[#a78bfa]/40 rounded-xl p-4 text-sm max-w-xl space-y-2.5">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-[#a78bfa]/15 text-[#a78bfa] border border-[#a78bfa]/30 font-mono">
                              {generalKnowledgeAnswer.badge}
                            </span>
                          </div>
                          <p className="text-xs text-[#fafafa] leading-relaxed whitespace-pre-line">
                            {generalKnowledgeAnswer.text}
                          </p>
                          <p className="text-[11px] text-[#71717a] italic pt-1 border-t border-[#27272a]">
                            {generalKnowledgeAnswer.note}
                          </p>
                        </div>
                      </div>
                    )}

                    {boundaryChoice === 'course-only' && (
                      <div className="flex items-start gap-3.5 max-w-3xl pl-11">
                        <div className="bg-[#121215] border border-[#34d399]/40 rounded-xl p-4 text-sm max-w-xl space-y-2.5">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-[#34d399]/15 text-[#34d399] border border-[#34d399]/30 font-mono">
                              {courseOnlyAnswer.badge}
                            </span>
                          </div>
                          <p className="text-xs text-[#fafafa] leading-relaxed whitespace-pre-line">
                            {courseOnlyAnswer.text}
                          </p>
                          <p className="text-[11px] text-[#71717a] italic pt-1 border-t border-[#27272a]">
                            {courseOnlyAnswer.note}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              }

              return null;
            })}

            <div ref={chatBottomRef} />
          </div>

          {/* Anchored Bottom Composer */}
          <TutorComposer onSendMessage={handleSendMessage} />
        </section>

        {/* ==================== RIGHT PANE: SOURCES VIEWER (~38% or Drawer) ==================== */}
        <SourcePanel
          sources={sources}
          activeSource={activeSource}
          isOpen={isSourcesOpen}
          onClose={() => setIsSourcesOpen(false)}
          onSelectSource={handleSelectSource}
          isMobile={isMobile}
        />
      </div>
    </div>
  );
}

