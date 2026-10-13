import React, { useState, useEffect, useRef } from 'react';
import Citation from './Citation';
import SourcePanel from './SourcePanel';
import OutsideMaterialNotice from './OutsideMaterialNotice';
import FollowUpActions from './FollowUpActions';
import TutorComposer from './TutorComposer';
import tutorApi from '../../api/tutorApi';
export default function CourseTutorView({
  user,
  courseId,
  courseName = 'Course Overview',
}) {
  const [sources, setSources] = useState([]);
  const [messages, setMessages] = useState([
    {
      id: 'welcome-msg',
      sender: 'tutor',
      time: 'Just now',
      isGrounded: true,
      lead: `Hello! I am your AI study companion for ${courseName}. Ask me anything about your course materials or select a topic to begin studying.`,
      text: `Hello! I am your AI study companion for ${courseName}. Ask me anything about your course materials or select a topic to begin studying.`,
      citations: [],
      sourcesSummary: [],
    },
  ]);
  const [currentThreadId, setCurrentThreadId] = useState(null);
  const [activeSource, setActiveSource] = useState(2); // Default to Slide 18
  const [isSourcesOpen, setIsSourcesOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [boundaryChoice, setBoundaryChoice] = useState(null); // 'general' | 'course-only' | null
  const [_isTyping, setIsTyping] = useState(false);
  const chatBottomRef = useRef(null);

  // Initialize or load existing persistent tutor thread for this course
  useEffect(() => {
    if (!courseId) return;

    tutorApi.listThreads(courseId)
      .then((threads) => {
        if (Array.isArray(threads) && threads.length > 0) {
          const tid = threads[0].id;
          setCurrentThreadId(tid);
          return tutorApi.getThread(courseId, tid);
        } else {
          return tutorApi.createThread(courseId, { title: 'Persistent Tutor Session' })
            .then((newT) => {
              setCurrentThreadId(newT.id);
              return null;
            });
        }
      })
      .then((threadDetail) => {
        if (threadDetail?.messages && threadDetail.messages.length > 0) {
          const loaded = threadDetail.messages.map((m) => {
            const hasCitations = Array.isArray(m.citations) && m.citations.length > 0;
            return {
              id: m.id,
              sender: m.role === 'user' ? 'student' : 'tutor',
              time: 'Earlier',
              text: m.content,
              lead: m.content,
              isGrounded: m.status === 'answered' || hasCitations,
              citations: m.citations || [],
              sourcesSummary: hasCitations
                ? m.citations.map((c, idx) => ({
                    num: idx + 1,
                    label: `${c.source_filename || 'Course Document'} · P.${c.page_number || 1}`,
                    type: 'PDF',
                    sourceId: c.source_id,
                  }))
                : [],
            };
          });
          setMessages(loaded);
        }
      })
      .catch((err) => {
        console.warn('Persistent tutor thread load warning:', err);
      });
  }, [courseId]);

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

  const handleSendMessage = async (text) => {
    const studentMsg = {
      id: `msg-${Date.now()}`,
      sender: 'student',
      time: 'Just now',
      text,
    };

    setMessages((prev) => [...prev, studentMsg]);
    setIsTyping(true);
    setTimeout(() => {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);

    if (courseId && currentThreadId) {
      try {
        const assistantMsg = await tutorApi.postMessage(courseId, currentThreadId, {
          question: text,
        });

        const hasCits = Array.isArray(assistantMsg.citations) && assistantMsg.citations.length > 0;
        const liveTutorMsg = {
          id: assistantMsg.id || `msg-${Date.now() + 1}`,
          sender: 'tutor',
          time: 'Just now',
          isGrounded: assistantMsg.status === 'answered' || hasCits,
          lead: assistantMsg.content,
          text: assistantMsg.content,
          citations: assistantMsg.citations || [],
          sourcesSummary: hasCits
            ? assistantMsg.citations.map((c, idx) => ({
                num: idx + 1,
                label: `${c.source_filename || 'Course Document'} · P.${c.page_number || 1}`,
                type: 'PDF',
                sourceId: c.source_id,
              }))
            : [],
        };

        if (hasCits) {
          const newSources = assistantMsg.citations.map((c, idx) => ({
            id: idx + 1,
            num: idx + 1,
            title: c.source_filename || 'Course Document',
            meta: `Page ${c.page_number || 1} · Semantic relevance ${(c.relevance_score ? Math.round(c.relevance_score * 100) : 95)}%`,
            type: 'PDF',
            quote: c.snippet || c.exact_quote || 'Course material reference text.',
          }));
          setSources(newSources);
        }

        setMessages((prev) => [...prev, liveTutorMsg]);
        setIsTyping(false);
        setTimeout(() => {
          chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
        return;
      } catch (err) {
        console.warn('Live tutor query failed:', err);
        const errorTutorMsg = {
          id: `msg-${Date.now() + 1}`,
          sender: 'tutor',
          time: 'Just now',
          isGrounded: false,
          lead: err?.response?.data?.detail || 'I encountered an issue connecting to the tutor service. Please ensure your course materials are indexed and try again.',
          text: err?.response?.data?.detail || 'I encountered an issue connecting to the tutor service. Please ensure your course materials are indexed and try again.',
          citations: [],
          sourcesSummary: [],
        };
        setMessages((prev) => [...prev, errorTutorMsg]);
        setIsTyping(false);
        setTimeout(() => {
          chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
        return;
      }
    } else {
      const notReadyMsg = {
        id: `msg-${Date.now() + 1}`,
        sender: 'tutor',
        time: 'Just now',
        isGrounded: false,
        lead: 'Tutor session is initializing. Please wait a moment and try again.',
        text: 'Tutor session is initializing. Please wait a moment and try again.',
        citations: [],
        sourcesSummary: [],
      };
      setMessages((prev) => [...prev, notReadyMsg]);
      setIsTyping(false);
      setTimeout(() => {
        chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  const handleFollowUpAction = (_actionId, label) => {
    handleSendMessage(label);
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
                  Current focus: {courseName}
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

              // Tutor Response
              if (msg.sender === 'tutor') {
                return (
                  <div key={msg.id} className="flex items-start gap-3.5 max-w-3xl">
                    <div className="w-8 h-8 rounded-full bg-[#a78bfa]/20 border border-[#a78bfa]/50 flex items-center justify-center text-[#a78bfa] shrink-0 mt-0.5">
                      <span className="material-symbols-outlined text-base">smart_toy</span>
                    </div>

                    <div className="flex-1 space-y-4">
                      {/* Main Answer Bubble */}
                      <div className="bg-[#121215] border border-[#27272a] rounded-2xl rounded-tl-sm p-5 space-y-4 text-[#fafafa] text-[15px] leading-relaxed shadow-sm">
                        <p className="text-[#fafafa] text-[15px] leading-relaxed whitespace-pre-wrap">
                          {msg.lead || msg.text}{' '}
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

