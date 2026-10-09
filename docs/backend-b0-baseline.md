# Backend Baseline & API Contracts (Phase B0 Checkpoint)

**Status:** `VERIFIED BASELINE (PHASE B0 PASS)`  
**Branch:** `rudresh/backend-b0-baseline`  
**Date:** October 9, 2026  

---

## 1. Overview & Scope Boundary

This document records the verified backend baseline, architecture, and API contracts for the Edvora personalized AI study companion platform as of Phase B0.

### Scope Boundary
- **Phase B0 Scope:** Baseline verification, regression testing, API contract snapshot, and documentation.
- **Strict Prohibition in B0:** No database models, no PostgreSQL/pgvector, no SQLAlchemy, no Alembic migrations, no architectural refactors, and no frontend modifications.
- **Phase B1 Scope:** Phase B1 will introduce relational database persistence (PostgreSQL + SQLAlchemy), Alembic migrations, and the core Course architecture (`Course`, `CourseMaterial`, `User`, `Enrollment`).

---

## 2. High-Level Current Backend Architecture

The backend is built with **FastAPI** (`backend/app/main.py`) and organized around modular service layers (`backend/app/services/`):

1. **Document Ingestion & Chunking:**
   - Text extracted page-by-page from PDFs using PyMuPDF (`pymupdf`) with fallback to `pypdf` (`pdf_service.py`).
   - Text split into word-level overlapping chunks (800 words window, 120 words overlap) while preserving page and filename provenance (`chunk_service.py`, `ingestion_service.py`).
2. **Dense Vector Embeddings & Semantic Retrieval:**
   - Local dense vector embeddings computed via SentenceTransformers `all-MiniLM-L6-v2` (`embedding_service.py`).
   - Cosine similarity ranking via dot-product between query and chunk embeddings (`retrieval_service.py`).
3. **LLM Integration & Resilient Fallback:**
   - Powered by Google GenAI (`google-genai` SDK) via `llm_service.py`.
   - Automatic multi-model fallback dispatch (`gemini-3.8-flash` primary → `gemini-3.5-flash-lite` fallback) on retryable error codes (e.g., 503 `UNAVAILABLE`, 429 `RESOURCE_EXHAUSTED`, timeout).
4. **Structured Curriculum & Topic Extraction:**
   - Extraction of academic topics and granular concepts from text chunks as structured JSON via LLM prompts (`topic_service.py`).
5. **Grounded AI Tutor (RAG):**
   - Context-grounded generation restricted strictly to retrieved PDF chunks with exact citations (`rag_service.py`).
   - Strict no-false-citation boundary that strips citations when answers cannot be found.
6. **Adaptive Quiz Generation & Grounding:**
   - Multi-stage pipeline: relevant chunk retrieval → candidate question generation → format & structure validation → repetition avoidance → batch grounding verification via LLM (`quiz_service.py`, `question_grounding_service.py`, `question_similarity_service.py`).
7. **Evaluation, Learner Modeling & Recommendations:**
   - Student answer normalization and verification (`quiz_evaluation_service.py`).
   - Concept/topic mastery tracking and level derivation (`mastery_service.py`, `learner_model_service.py`).
   - Dynamic study recommendations for weak concepts with mastery score $< 0.50$ (`recommendation_service.py`).

---

## 3. Current In-Memory Stores

The Phase B0 backend uses in-memory Python dictionaries to hold runtime state. These will be replaced in subsequent phases by persistent database tables:

| In-Memory Store | Location | Structure | Target Persistent State |
| :--- | :--- | :--- | :--- |
| **`documents`** | `app/services/document_store.py` | `documents[filename] = {"chunks": list[dict], "topics": list[dict]}` | Relational `courses`, `sources`, and `content_units` tables (B1/B2) |
| **`learner_model`** | `app/services/learner_model_service.py` | `learner_model[topic][concept] = {"correct_answers": int, "total_questions": int, "mastery": float, "level": str}` | Persistent learner mastery / BKT tables linked to user and course |
| **`question_history`** | `app/services/question_history_service.py` | `question_history[topic][concept] = list[str]` | Persistent `quiz_questions` and `quiz_attempts` history tables |
| **`uploads` (Disk)** | `backend/data/uploads/` | Local directory storing uploaded PDF files | Persistent object/file storage with managed metadata |

---

## 4. Current FastAPI Endpoint Contracts

All routes are mounted in `app/main.py` and accept/return JSON (with the exception of `/documents/upload` which accepts `multipart/form-data`).

### 1. Root & Health Check

#### `GET /`
- **Description:** Returns API status and service name.
- **Request:** None.
- **Response (200 OK):**
```json
{
  "message": "Personalized AI Study Companion API",
  "status": "running"
}
```

#### `GET /health`
- **Description:** Service health check endpoint.
- **Request:** None.
- **Response (200 OK):**
```json
{
  "status": "healthy"
}
```

---

### 2. Document Management

#### `POST /documents/upload`
- **Description:** Uploads a PDF document, chunks it with page metadata, extracts topics and concepts via LLM, and caches the result in the in-memory `document_store`.
- **Request:** Multipart Form Data
  - `file`: PDF file binary (`application/pdf`). Rejects non-PDFs with HTTP 400.
- **Response (200 OK):**
```json
{
  "message": "PDF uploaded and processed successfully",
  "filename": "physics.pdf",
  "path": "data\\uploads\\physics.pdf",
  "chunks_created": 5,
  "topics_created": 5,
  "topics": [
    {
      "name": "Fundamentals of Ultrasonic Waves",
      "concepts": [
        "Definition and frequency range",
        "Wave relation (v = fλ)"
      ]
    }
  ]
}
```
- **Error Responses:**
  - `400 Bad Request`: When uploaded file is not a PDF (`"Only PDF files are supported."`).

---

### 3. AI Tutor

#### `POST /tutor/ask`
- **Description:** Ask a grounded question against an ingested document using semantic chunk retrieval and LLM synthesis.
- **Request:** JSON
```json
{
  "question": "What is the piezoelectric effect?",
  "filename": "physics.pdf"
}
```
- **Response (200 OK):**
```json
{
  "answer": "Based on the provided study material, the piezoelectric effect occurs when...",
  "sources": [
    {
      "filename": "physics.pdf",
      "page": 2,
      "score": 0.6531
    }
  ]
}
```
- **Out-of-Scope Response (200 OK):**
```json
{
  "answer": "I could not find this information in the provided material.",
  "sources": []
}
```
- **Error Responses:**
  - `404 Not Found`: When `filename` does not exist in `document_store`.

---

### 4. Practice Quiz

#### `POST /quiz/generate`
- **Description:** Generates an adaptive, grounded MCQ quiz for a specific topic and concept from an uploaded document.
- **Request:** JSON
```json
{
  "filename": "physics.pdf",
  "topic": "Fundamentals of Ultrasonic Waves",
  "concept": "Definition and frequency range",
  "num_questions": 5
}
```
  - `num_questions`: Integer between 1 and 10 (defaults to 5).
- **Response (200 OK):**
```json
{
  "filename": "physics.pdf",
  "topic": "Fundamentals of Ultrasonic Waves",
  "concept": "Definition and frequency range",
  "questions": [
    {
      "question": "Which frequency defines the threshold of ultrasonic waves?",
      "options": [
        "Greater than 20 kHz",
        "Below 20 Hz",
        "Between 20 Hz and 20 kHz",
        "Exactly 10 kHz"
      ],
      "correct_answer": "Greater than 20 kHz",
      "difficulty": "easy",
      "explanation": "Ultrasonics refers to sound waves whose frequency exceeds human hearing (20 kHz).",
      "sources": [
        {
          "filename": "physics.pdf",
          "page": 1
        }
      ]
    }
  ]
}
```
- **Error Responses:**
  - `404 Not Found`: When document is not found.
  - `400 Bad Request`: If `num_questions < 1` or `num_questions > 10`.
  - `500 Internal Server Error`: On generation failure.

#### `POST /quiz/evaluate`
- **Description:** Evaluates a single student answer for an individual question.
- **Request:** JSON
```json
{
  "question": {
    "question": "What is the frequency threshold of ultrasound?",
    "correct_answer": "Greater than 20 kHz",
    "explanation": "Ultrasonic waves have frequencies above 20 kHz.",
    "sources": [{"filename": "physics.pdf", "page": 1}]
  },
  "selected_answer": "Greater than 20 kHz"
}
```
- **Response (200 OK):**
```json
{
  "is_correct": true,
  "selected_answer": "Greater than 20 kHz",
  "correct_answer": "Greater than 20 kHz",
  "explanation": "Ultrasonic waves have frequencies above 20 kHz.",
  "sources": [
    {
      "filename": "physics.pdf",
      "page": 1
    }
  ]
}
```

#### `POST /quiz/submit`
- **Description:** Submits full quiz answers, evaluates each item, updates concept mastery, and returns scores.
- **Request:** JSON
```json
{
  "topic": "Fundamentals of Ultrasonic Waves",
  "concept": "Definition and frequency range",
  "questions": [
    {
      "question": "What is the frequency threshold of ultrasound?",
      "correct_answer": "Greater than 20 kHz",
      "explanation": "...",
      "sources": []
    }
  ],
  "selected_answers": {
    "0": "Greater than 20 kHz"
  }
}
```
- **Response (200 OK):**
```json
{
  "topic": "Fundamentals of Ultrasonic Waves",
  "concept": "Definition and frequency range",
  "results": [
    {
      "question_index": 0,
      "is_correct": true,
      "selected_answer": "Greater than 20 kHz",
      "correct_answer": "Greater than 20 kHz",
      "explanation": "...",
      "sources": []
    }
  ],
  "score": 1,
  "total": 1,
  "quiz_mastery": 1.0,
  "learner_mastery": {
    "correct_answers": 1,
    "total_questions": 1,
    "mastery": 1.0,
    "level": "strong"
  }
}
```
- **Error Responses:**
  - `400 Bad Request`: If `questions` list is empty.

---

### 5. Recommendations

#### `GET /recommendations/`
- **Description:** Scans the learner model for concepts with `level == "weak"` (mastery $< 0.50$).
- **Request:** None.
- **Response (200 OK):**
```json
{
  "weak_concepts": [
    {
      "topic": "Fundamentals of Ultrasonic Waves",
      "concept": "Wave relation (v = fλ)",
      "mastery": 0.25,
      "recommendation": "Practice this concept"
    }
  ],
  "total_weak_concepts": 1
}
```

---

## 5. Phase 0 Behavioral Guarantees & Regression Boundaries

The following behaviors were established and verified during Phase 0 and must remain strictly preserved:

1. **PDF Extraction & Page Provenance:**
   - Multi-page PDFs extract with 100% page fidelity (`pymupdf` primary, `pypdf` fallback).
   - Each chunk retains exact source provenance: `id`, `source.filename`, and `source.page`.
2. **Semantic Retrieval:**
   - Chunks are vectorized using `all-MiniLM-L6-v2`.
   - Domain-specific queries rank relevant pages first (e.g., Economics Marginal Principle query retrieves Page 6 and Page 7).
3. **Grounded Tutor Responses:**
   - RAG responses use exclusively the provided chunk content. Outside knowledge and hallucinations are rejected by prompt directives.
4. **No-False-Citation Boundary:**
   - If a student asks an out-of-scope question (e.g., quantum entanglement in an economics course), the tutor states information is not found and returns `sources: []`. Unrelated chunks are never attached as false citations.
5. **Quiz Validation:**
   - `_validate_question(question)` returns `(is_valid, reason)`. The filtering logic strictly inspects the boolean value to reject invalid shapes, duplicate options, missing correct answers, or non-4-option questions.
   - Questions testing document structure/layout (e.g. "Which topic is on page 3?") are systematically filtered out.
6. **Quiz Evaluation:**
   - Case-insensitive trimming and exact matching against the correct answer.
7. **Mastery Non-Mutation (No Phantom Increments):**
   - Constructing a submission response calls `get_concept_mastery(topic, concept)` (pure read) rather than mutating state. Mastery updates occur exactly once per attempted question.
8. **Adaptive Recommendations:**
   - Concepts with mastery $< 0.50$ are tagged `weak` and exposed via `/recommendations/`.
9. **Resilient Gemini Fallback:**
   - When the primary model (`gemini-3.8-flash`) hits a transient error (e.g., HTTP 503 high demand or HTTP 429 quota exhaustion), the system automatically logs the event and falls back to `gemini-3.5-flash-lite`, preventing request failures.

---

## 6. Frontend ↔ Backend Integration Points

The existing frontend integration points reside in `frontend/src/components/StudyWorkspace.jsx`:
- **Line 47:** `POST http://127.0.0.1:8000/documents/upload`
- **Line 105:** `POST http://127.0.0.1:8000/tutor/ask`
- **Lines 152, 193:** `POST http://127.0.0.1:8000/quiz/generate`
- **Line 231:** `POST http://127.0.0.1:8000/quiz/submit`
- **Line 267:** `GET http://127.0.0.1:8000/recommendations/`

*Note: Phase 1 frontend workspaces (`CourseWorkspacePage`, `CourseMaterialsPage`, `CoursePracticePage`, `CourseProgressPage`, `CourseTutorView`) currently consume mock datasets (`frontend/src/data/mock*.js`) pending completion of Phase B1–B4 backend services.*

---

## 7. Known B0 Limitations & Infrastructure Notes

1. **Standalone Test Script Execution:**
   - Test files in `backend/test_*.py` are standalone Python scripts rather than modular `pytest` test functions. Running standard `pytest` executes LLM and ingestion logic during collection/import time. A formalized test suite with mocked LLM and embedding layers will be introduced in later phases.
2. **Gitignored Assets:**
   - `.env` and `backend/data/uploads/` are intentionally gitignored. New local clones require configuring `.env` from `.env.example` and uploading or generating test documents.
3. **Windows UTF-8 Console Output:**
   - Windows consoles running `cp1252` encoding may encounter encoding errors on scientific symbols (e.g., `\u221a`). Execution should set `PYTHONIOENCODING=utf-8` or `sys.stdout.reconfigure(encoding="utf-8")`.
4. **LLM Free-Tier Rate Limits:**
   - Consecutive LLM calls may trigger 503 spikes or 429 daily quotas on primary models; the multi-model fallback in `llm_service.py` is essential for continuous test and runtime resilience.

