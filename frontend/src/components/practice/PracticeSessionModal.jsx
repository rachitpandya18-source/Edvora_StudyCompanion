import React, { useState } from 'react';
import practiceApi from '../../api/practiceApi';

/**
 * PracticeSessionModal
 * Interactive practice modal supporting live generated assessment questions,
 * multi-question navigation, evaluation submission, and BKT mastery feedback.
 */
export default function PracticeSessionModal({
  isOpen = false,
  sessionConfig = null,
  onClose,
  onAttemptCompleted,
}) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState(sessionConfig?.initialAnswers || {});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState(sessionConfig?.initialEvaluation || null);
  const [submitError, setSubmitError] = useState(null);

  if (!isOpen || !sessionConfig) return null;

  const {
    courseId,
    assessmentId,
    attemptId,
    title = 'Adaptive Practice Session',
    topic = 'Course Topics',
    questions = [],
    difficulty = 'Adaptive',
    type = 'Multiple Choice',
  } = sessionConfig;

  const defaultQuestion = {
    id: 'demo-q1',
    prompt:
      'Which of the following best describes the core principle governing this topic in your course materials?',
    options: [
      { id: 'opt-a', text: 'It establishes foundational equilibrium relationships and conservation principles.', is_correct: true },
      { id: 'opt-b', text: 'It only applies in isolated, non-standard experimental conditions.' },
      { id: 'opt-c', text: 'It completely eliminates all state variation across the system.' },
      { id: 'opt-d', text: 'It is solely an empirical approximation with no physical or theoretical basis.' },
    ],
    explanation:
      'The foundational principles established in your course materials define the equilibrium relationships and governing dynamics for this subject.',
  };

  const rawQuestions = questions.length > 0 ? questions : [defaultQuestion];
  const activeQuestions = rawQuestions.map((q) => {
    let opts = [];
    if (q.options && Array.isArray(q.options)) {
      opts = q.options.map((opt, i) =>
        typeof opt === 'string' ? { id: opt, text: opt } : { id: opt.id || opt.text || `opt-${i}`, text: opt.text || opt.id || String(opt), is_correct: opt.is_correct }
      );
    } else if (q.options_json && Array.isArray(q.options_json)) {
      opts = q.options_json.map((opt) => ({
        id: opt,
        text: opt,
      }));
    }
    return {
      ...q,
      options: opts,
    };
  });

  const currentQ = activeQuestions[currentIdx] || activeQuestions[0];
  const questionCount = activeQuestions.length;
  const currentAnswer = selectedAnswers[currentQ.id];

  const evalAns = evaluationResult?.answers?.find(
    (a) => String(a.question_id) === String(currentQ.id)
  );

  const rawScore = evaluationResult?.score ?? 0;
  const maxScore = evaluationResult?.max_score ?? questionCount ?? 1;
  const safePercentage = Math.min(
    100,
    Math.max(
      0,
      evaluationResult?.percentage !== undefined && evaluationResult?.percentage !== null
        ? Math.round(evaluationResult.percentage)
        : Math.round((rawScore / (maxScore || 1)) * 100)
    )
  );

  const handleSelectOption = (optValue) => {
    if (!evaluationResult) {
      setSelectedAnswers((prev) => ({
        ...prev,
        [currentQ.id]: optValue,
      }));
    }
  };

  const handleSubmitAttempt = async () => {
    if (!currentAnswer && !Object.keys(selectedAnswers).length) return;

    setIsSubmitting(true);
    setSubmitError(null);

    if (courseId && assessmentId && attemptId) {
      try {
        const answers = activeQuestions
          .filter((q) => selectedAnswers[q.id] !== undefined)
          .map((q) => ({
            question_id: q.id,
            student_answer: String(selectedAnswers[q.id]),
          }));

        const result = await practiceApi.submitAttempt(
          courseId,
          assessmentId,
          attemptId,
          answers
        );

        setEvaluationResult(result);
        setIsSubmitting(false);
        onAttemptCompleted?.(result);
        return;
      } catch (err) {
        console.error('Practice submission error:', err);
        setSubmitError(err.message || 'Failed to submit practice attempt. Please try again.');
        setIsSubmitting(false);
        return;
      }
    }

    // If no courseId/attemptId, fail truthfully instead of synthesizing fake score
    setSubmitError('Unable to record practice attempt: missing active course or assessment session.');
    setIsSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Card */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full max-w-2xl bg-[#0c0c0f] border border-[#27272a] rounded-xl shadow-2xl z-10 overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="h-14 px-6 border-b border-[#27272a] flex items-center justify-between bg-[#0f0f12] shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-[#34d399] animate-pulse" />
            <h3 className="text-sm font-semibold text-white tracking-tight">
              {title}
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
            aria-label="Close practice session"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Parameter Strip & Question Pills */}
          <div className="p-3.5 rounded-lg bg-[#121215] border border-[#27272a] flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-[#a1a1aa]">
            <div className="flex items-center gap-2">
              <span className="text-[#a78bfa] font-semibold">Topic:</span>
              <span className="text-white truncate max-w-[200px]">
                {currentQ.concept_title || currentQ.concept_name || topic}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#a78bfa] font-semibold">Question:</span>
              <span className="text-white">{currentIdx + 1} of {questionCount}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#a78bfa] font-semibold">Difficulty:</span>
              <span className="text-white">{difficulty}</span>
            </div>

            {/* Question Quick Jump Pills */}
            {questionCount > 1 && (
              <div className="w-full pt-2 border-t border-[#27272a]/70 flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] text-[#71717a] mr-1">Questions:</span>
                {activeQuestions.map((q, idx) => {
                  const isCur = idx === currentIdx;
                  const ansItem = evaluationResult?.answers?.find(
                    (a) => String(a.question_id) === String(q.id)
                  );
                  let pillStyle =
                    'border-[#27272a] bg-[#18181b] text-[#a1a1aa] hover:text-white hover:border-[#3f3f46]';
                  if (evaluationResult) {
                    if (ansItem?.is_correct === true) {
                      pillStyle = 'border-[#059669] bg-[#065f46]/30 text-[#34d399]';
                    } else if (ansItem?.is_correct === false) {
                      pillStyle = 'border-[#dc2626] bg-[#7f1d1d]/30 text-[#f87171]';
                    } else {
                      pillStyle = 'border-[#27272a] bg-[#18181b] text-[#71717a]';
                    }
                  } else if (selectedAnswers[q.id] !== undefined) {
                    pillStyle = 'border-[#a78bfa]/50 bg-[#a78bfa]/10 text-[#a78bfa]';
                  }
                  return (
                    <button
                      key={q.id || idx}
                      type="button"
                      onClick={() => setCurrentIdx(idx)}
                      className={`w-7 h-7 rounded-md text-xs font-mono font-semibold border flex items-center justify-center transition-all cursor-pointer ${pillStyle} ${
                        isCur ? 'ring-2 ring-[#a78bfa]' : ''
                      }`}
                      title={`Jump to Question ${idx + 1}`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Interactive Question Card */}
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-mono text-[#a1a1aa]">
              <span>Question {currentIdx + 1}</span>
              <span className="px-2 py-0.5 rounded bg-[#18181b] border border-[#27272a] text-[#a78bfa]">
                {type}
              </span>
            </div>

            <p className="text-[15px] font-medium text-white leading-relaxed">
              {currentQ.prompt}
            </p>

            {/* Options */}
            <div className="space-y-2.5 pt-1">
              {(currentQ.options || []).map((opt, oIdx) => {
                const optId = opt.id || `opt-${oIdx}`;
                const optText = opt.text || opt.id || String(opt);

                const isSelected =
                  currentAnswer === optId ||
                  currentAnswer === optText ||
                  evalAns?.student_answer === optId ||
                  evalAns?.student_answer === optText;

                let borderStyle =
                  'border-[#27272a] hover:border-[#3f3f46] bg-[#121215] text-[#fafafa]';
                let badge = null;

                if (evaluationResult) {
                  const isCorrectChoice =
                    evalAns?.correct_answer !== undefined && evalAns?.correct_answer !== null
                      ? optId === evalAns.correct_answer || optText === evalAns.correct_answer
                      : opt.is_correct === true || (isSelected && evalAns?.is_correct === true);

                  if (isCorrectChoice) {
                    borderStyle =
                      'border-[#059669] bg-[#065f46]/25 text-[#34d399] font-medium ring-1 ring-[#059669]/50';
                    badge = (
                      <span className="ml-auto text-xs font-semibold px-2 py-0.5 rounded bg-[#065f46] text-[#34d399] flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">check</span>
                        Correct
                      </span>
                    );
                  } else if (isSelected && !isCorrectChoice) {
                    borderStyle =
                      'border-[#dc2626] bg-[#7f1d1d]/20 text-[#f87171] font-medium ring-1 ring-[#dc2626]/50';
                    badge = (
                      <span className="ml-auto text-xs font-semibold px-2 py-0.5 rounded bg-[#7f1d1d] text-[#f87171] flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">close</span>
                        Your Answer
                      </span>
                    );
                  } else {
                    borderStyle = 'border-[#27272a] bg-[#121215]/50 text-[#71717a] opacity-60';
                  }
                } else if (isSelected) {
                  borderStyle = 'border-[#a78bfa] bg-[#18181c] text-white ring-1 ring-[#a78bfa]/30';
                }

                return (
                  <button
                    key={optId}
                    type="button"
                    onClick={() => handleSelectOption(optId)}
                    className={`w-full p-3.5 rounded-lg border text-left text-xs sm:text-sm font-medium transition-all flex items-start gap-3 cursor-pointer ${borderStyle}`}
                  >
                    <span className="w-5 h-5 rounded-full border border-current flex items-center justify-center shrink-0 mt-0.5 text-xs font-mono font-bold uppercase">
                      {String.fromCharCode(65 + oIdx)}
                    </span>
                    <span className="flex-1 leading-snug">{optText}</span>
                    {badge}
                  </button>
                );
              })}
            </div>

            {/* Error banner on failed submission */}
            {submitError && (
              <div className="p-3.5 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/30 text-xs sm:text-sm text-[#f87171] flex items-center justify-between gap-2 animate-in fade-in duration-150">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-base shrink-0">error</span>
                  <span>{submitError}</span>
                </div>
                <button
                  type="button"
                  onClick={handleSubmitAttempt}
                  className="px-2.5 py-1 rounded bg-[#ef4444]/20 hover:bg-[#ef4444]/30 text-white font-medium text-xs cursor-pointer shrink-0"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Feedback & Review on evaluation */}
            {evaluationResult && (
              <div className="p-4 rounded-lg bg-[#18181b] border border-[#27272a] text-xs sm:text-sm text-[#fafafa] space-y-3 animate-in fade-in duration-150">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`material-symbols-outlined text-base ${
                        evalAns?.is_correct ? 'text-[#34d399]' : 'text-[#f87171]'
                      }`}
                    >
                      {evalAns?.is_correct ? 'check_circle' : 'cancel'}
                    </span>
                    <span
                      className={`font-semibold ${
                        evalAns?.is_correct ? 'text-[#34d399]' : 'text-[#f87171]'
                      }`}
                    >
                      {evalAns?.is_correct ? 'Correct' : 'Needs Review'}
                    </span>
                    <span className="text-[#71717a] font-mono text-xs">
                      ({evalAns?.marks_awarded ?? (evalAns?.is_correct ? 1 : 0)} /{' '}
                      {currentQ.marks ?? 1} marks)
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-xs font-semibold text-[#a78bfa]">
                      Score: {safePercentage}% ({rawScore}/{maxScore})
                    </span>
                  </div>
                </div>

                {(evalAns?.concept_title ||
                  evalAns?.concept_name ||
                  currentQ.concept_title ||
                  currentQ.concept_name) && (
                  <div className="text-xs text-[#a1a1aa] flex items-center gap-1.5 font-mono">
                    <span className="text-[#a78bfa]">Concept:</span>
                    <span className="text-zinc-200">
                      {evalAns?.concept_title ||
                        evalAns?.concept_name ||
                        currentQ.concept_title ||
                        currentQ.concept_name}
                    </span>
                  </div>
                )}

                <div className="pt-2 border-t border-[#27272a]/70">
                  <div className="text-xs font-semibold text-[#a1a1aa] mb-1 font-mono uppercase tracking-wider">
                    Explanation
                  </div>
                  <p className="text-[#d4d4d8] leading-relaxed text-xs sm:text-sm">
                    {evalAns?.explanation ||
                      evalAns?.feedback ||
                      currentQ.explanation ||
                      'Bayesian Knowledge Tracing (BKT) updated your concept mastery probability.'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 px-6 border-t border-[#27272a] bg-[#0f0f12] flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2">
            {questionCount > 1 && currentIdx > 0 && (
              <button
                type="button"
                onClick={() => setCurrentIdx((i) => i - 1)}
                className="px-3 py-2 rounded-lg border border-[#27272a] text-xs text-[#a1a1aa] hover:text-white cursor-pointer"
              >
                Previous
              </button>
            )}
            {questionCount > 1 && currentIdx < questionCount - 1 && (
              <button
                type="button"
                onClick={() => setCurrentIdx((i) => i + 1)}
                className="px-3 py-2 rounded-lg border border-[#27272a] text-xs text-[#a1a1aa] hover:text-white cursor-pointer"
              >
                Next Question
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-[#27272a] text-xs font-medium text-[#a1a1aa] hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
            >
              {evaluationResult ? 'Close' : 'Cancel'}
            </button>

            {!evaluationResult ? (
              <button
                type="button"
                disabled={!currentAnswer || isSubmitting}
                onClick={handleSubmitAttempt}
                className="px-5 py-2 rounded-lg bg-[#a78bfa] hover:bg-[#c4b5fd] text-[#0a0012] disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>{isSubmitting ? 'Evaluating...' : 'Submit Answers'}</span>
                <span className="material-symbols-outlined text-sm">check</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 rounded-lg bg-[#34d399] hover:bg-[#6ee7b7] text-[#003318] text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>Complete Session</span>
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
