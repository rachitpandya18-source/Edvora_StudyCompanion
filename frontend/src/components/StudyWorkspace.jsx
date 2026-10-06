import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import "katex/dist/katex.min.css";
import "../App.css";

export default function StudyWorkspace({ onBack }) {
  const [file, setFile] = useState(null);
  const [filename, setFilename] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);

  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [quiz, setQuiz] = useState([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizError, setQuizError] = useState("");
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [submittedAnswers, setSubmittedAnswers] = useState({});

  const [topics, setTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState("");
  const [selectedConcept, setSelectedConcept] = useState("");
  const [recommendations, setRecommendations] = useState([]);

  // Upload PDF
  const uploadDocument = async () => {
    if (!file) {
      setUploadMessage("Please select a PDF first.");
      return;
    }

    setUploading(true);
    setUploadMessage("");
    setAnswer("");
    setSources([]);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        "http://127.0.0.1:8000/documents/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setFilename(data.filename);
      setTopics(data.topics || []);
      setSelectedTopic("");
      setSelectedConcept("");

      setQuiz([]);
      setSelectedAnswers({});
      setSubmittedAnswers({});
      setQuizError("");

      setUploadMessage(
        `Uploaded successfully — ${data.chunks_created} chunks created.`
      );
    } catch (error) {
      setUploadMessage(`Error: ${error.message}`);
      setFilename("");
    } finally {
      setUploading(false);
    }
  };

  const handleTopicChange = (event) => {
    const topicName = event.target.value;
    setSelectedTopic(topicName);

    const topic = topics.find((item) => item.name === topicName);
    const firstConcept = topic?.concepts?.[0] || "";
    setSelectedConcept(firstConcept);
  };

  // Ask Tutor
  const askTutor = async () => {
    if (!question.trim()) return;

    if (!filename) {
      setAnswer("Please upload a document first.");
      return;
    }

    setLoading(true);
    setAnswer("");
    setSources([]);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/tutor/ask",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: question,
            filename: filename,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong");
      }

      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const generateQuiz = async () => {
    if (!filename) {
      setQuizError("Please upload a document first.");
      return;
    }

    if (!selectedTopic || !selectedConcept) {
      setQuizError("Please select a topic and concept.");
      return;
    }

    setQuizLoading(true);
    setQuizError("");
    setQuiz([]);
    setSelectedAnswers({});
    setSubmittedAnswers({});

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/quiz/generate",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            filename: filename,
            topic: selectedTopic,
            concept: selectedConcept,
            num_questions: 5,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Quiz generation failed");
      }

      setQuiz(data.questions || []);
    } catch (error) {
      setQuizError(`Error: ${error.message}`);
    } finally {
      setQuizLoading(false);
    }
  };

  const practiceConcept = async (topic, concept) => {
    setSelectedTopic(topic);
    setSelectedConcept(concept);

    setQuizError("");
    setQuizLoading(true);
    setQuiz([]);
    setSelectedAnswers({});
    setSubmittedAnswers({});

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/quiz/generate",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            filename,
            topic,
            concept,
            num_questions: 5,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to generate quiz");
      }

      setQuiz(data.questions || []);
    } catch (error) {
      setQuizError(error.message);
    } finally {
      setQuizLoading(false);
    }
  };

  const submitQuiz = async () => {
    if (!quiz.length) {
      return;
    }

    try {
      setQuizError("");

      const response = await fetch(
        "http://127.0.0.1:8000/quiz/submit",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            topic: selectedTopic,
            concept: selectedConcept,
            questions: quiz,
            selected_answers: selectedAnswers,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Quiz submission failed");
      }

      const results = {};
      data.results.forEach((result) => {
        results[result.question_index] = result;
      });

      setSubmittedAnswers(results);
      await fetchRecommendations();
    } catch (error) {
      setQuizError(error.message);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/recommendations/"
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load recommendations");
      }

      setRecommendations(data.weak_concepts || []);
    } catch (error) {
      console.error("Recommendation error:", error);
    }
  };

  return (
    <div className="app">
      {/* Top Navigation Bar */}
      <div className="w-full bg-[#111827] border-b border-white/10 px-6 py-3 flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 text-sm text-neutral-300 hover:text-white transition-colors cursor-pointer bg-transparent border-0 p-0"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          <span>Back to Edvora Home</span>
        </button>
        <div className="flex items-center gap-2 text-xs font-mono text-neutral-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>Companion Active</span>
        </div>
      </div>

      {/* Header */}
      <header className="header">
        <h1>Personalized AI Study Companion</h1>
        <p>Ask questions from your study material</p>
      </header>

      <main className="container">
        {/* Upload */}
        <section className="upload-card">
          <h2>📤 Upload Study Material</h2>

          <input
            type="file"
            accept=".pdf"
            onChange={(e) => {
              setFile(e.target.files[0]);
              setUploadMessage("");
            }}
          />

          <button onClick={uploadDocument} disabled={uploading || !file}>
            {uploading ? "Uploading..." : "Upload PDF"}
          </button>

          {uploadMessage && (
            <p className="upload-message">{uploadMessage}</p>
          )}
        </section>

        {/* Current Document */}
        {filename && (
          <section className="document-card">
            <h2>📚 Current Document</h2>
            <p>{filename}</p>
          </section>
        )}

        {filename && topics.length > 0 && (
          <section className="quiz-setup-card">
            <h2>📝 Take a Quiz</h2>

            <div className="quiz-field">
              <label>Topic</label>
              <select value={selectedTopic} onChange={handleTopicChange}>
                <option value="">Select a topic</option>
                {topics.map((topic, index) => (
                  <option key={index} value={topic.name}>
                    {topic.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="quiz-field">
              <label>Concept</label>
              <select
                value={selectedConcept}
                onChange={(e) => setSelectedConcept(e.target.value)}
                disabled={!selectedTopic}
              >
                <option value="">Select a concept</option>
                {(
                  topics.find((topic) => topic.name === selectedTopic)
                    ?.concepts || []
                ).map((concept, index) => (
                  <option key={index} value={concept}>
                    {concept}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={generateQuiz}
              disabled={quizLoading || !selectedTopic || !selectedConcept}
            >
              {quizLoading ? "Generating Quiz..." : "Generate Quiz"}
            </button>

            {quizError && <p className="quiz-error">{quizError}</p>}
          </section>
        )}

        {quiz.length > 0 && (
          <section className="quiz-card">
            <h2>🧠 Quiz</h2>
            <p className="quiz-info">
              {selectedTopic} → {selectedConcept}
            </p>

            {quiz.map((q, questionIndex) => (
              <div className="quiz-question" key={questionIndex}>
                <h3>
                  Q{questionIndex + 1}. {q.question}
                </h3>

                <div className="quiz-options">
                  {q.options.map((option, optionIndex) => (
                    <label className="quiz-option" key={optionIndex}>
                      <input
                        type="radio"
                        name={`question-${questionIndex}`}
                        value={option}
                        checked={selectedAnswers[questionIndex] === option}
                        onChange={() =>
                          setSelectedAnswers({
                            ...selectedAnswers,
                            [questionIndex]: option,
                          })
                        }
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}

            <button
              className="submit-quiz-button"
              onClick={submitQuiz}
              disabled={
                quiz.length === 0 ||
                Object.keys(selectedAnswers).length === 0
              }
            >
              Submit Quiz
            </button>
          </section>
        )}

        {Object.keys(submittedAnswers).length > 0 && (
          <div className="quiz-results">
            <h2>📊 Results</h2>

            {quiz.map((q, questionIndex) => {
              const result = submittedAnswers[questionIndex];
              if (!result) return null;

              return (
                <div
                  className={`quiz-result ${
                    result.is_correct ? "correct" : "incorrect"
                  }`}
                  key={questionIndex}
                >
                  <h3>
                    Q{questionIndex + 1} —{" "}
                    {result.is_correct ? "✅ Correct" : "❌ Incorrect"}
                  </h3>

                  <p>
                    <strong>Your answer:</strong>{" "}
                    {result.selected_answer || "No answer provided"}
                  </p>

                  {!result.is_correct && (
                    <p>
                      <strong>Correct answer:</strong> {result.correct_answer}
                    </p>
                  )}

                  {result.explanation && (
                    <div className="quiz-explanation">
                      <strong>Explanation:</strong>
                      <p>{result.explanation}</p>
                    </div>
                  )}

                  {result.sources && result.sources.length > 0 && (
                    <div className="quiz-sources">
                      <strong>📖 Source:</strong>
                      {result.sources.map((source, sourceIndex) => (
                        <span key={sourceIndex}>
                          {sourceIndex > 0 && " • "}
                          {source.filename} — Page {source.page}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {recommendations.length > 0 && (
          <div className="recommendations-section">
            <h2>📊 Your Learning Progress</h2>

            <div className="recommendation-header">
              <h3>⚠️ Needs Practice</h3>
              <p>
                Based on your recent quiz performance, these concepts need
                more practice.
              </p>
            </div>

            {recommendations.map((recommendation, index) => (
              <div className="recommendation-card" key={index}>
                <h3>{recommendation.concept}</h3>
                <p>
                  <strong>Topic:</strong> {recommendation.topic}
                </p>
                <p>
                  <strong>Mastery:</strong>{" "}
                  {Math.round(recommendation.mastery * 100)}%
                </p>
                <p>
                  <strong>Status:</strong> 🔴 Weak
                </p>
                <div className="recommendation-message">
                  💡 {recommendation.recommendation}
                </div>
                <button
                  className="practice-button"
                  onClick={() =>
                    practiceConcept(
                      recommendation.topic,
                      recommendation.concept
                    )
                  }
                >
                  Practice This Concept
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Ask Tutor */}
        <section className="question-card">
          <h2>Ask your Tutor</h2>
          <textarea
            placeholder="Ask something about your study material..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button onClick={askTutor} disabled={loading || !filename}>
            {loading ? "Thinking..." : "Ask Tutor"}
          </button>
        </section>

        {/* Answer */}
        {answer && (
          <section className="answer-card">
            <h2>🤖 AI Tutor</h2>
            <div className="answer">
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {answer}
              </ReactMarkdown>
            </div>

            {sources.length > 0 && (
              <div className="sources">
                <h3>📖 Sources</h3>
                {sources.map((source, index) => (
                  <div className="source" key={index}>
                    <strong>{source.filename}</strong>
                    <span>Page {source.page}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
