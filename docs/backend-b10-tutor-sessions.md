# Milestone B10: Multi-Turn Persistent Tutor & Conversational Learning Engine

## 1. Overview & Architecture

Milestone B10 transforms Edvora's AI study tutor from a single-turn, stateless Q&A endpoint into a **Multi-Turn Persistent Tutor and Conversational Learning Engine**. Learners can conduct deep, continuous tutoring dialogues scoped to a course, refer back to previous explanations or steps, maintain distinct conversation threads, and preserve authentic source citations across conversational turns.

### Key Architectural Tenets & Invariants
- **Course & Student Scoping:** Every conversational thread (`TutorThread`) is strictly tied to a `Course` and a `Student` (via `student_id`). Cross-course or cross-student leakage is prevented with HTTP 404 responses.
- **Bounded Conversational Window:** The engine injects a sliding window of the most recent turns (`CONVERSATIONAL_WINDOW_LIMIT = 6` messages, 3 user/assistant turns) into the LLM context prompt to preserve continuity without context blowup or attention drift.
- **Strict Grounding & Refusal Heritage:** Reuses the verified B2 semantic retrieval infrastructure (`search_course_content`) and B4 grounding evaluation protocols (`NEGATIVE_GROUNDING_PHRASES`, relevance thresholds). Out-of-scope queries return clean refusals with empty citations.
- **Zero-Material Safeguard:** Courses without uploaded or indexed content return `no_course_material` deterministically without dispatching expensive upstream LLM calls.
- **Citation Persistence:** Assistant citations (`TutorCitation`) are serialized into database JSON columns on each turn and reconstructed when retrieving historical thread transcripts.
- **Strict Backward Compatibility:** Preserves `POST /courses/{course_id}/tutor/ask` and legacy `POST /tutor/ask` completely intact with identical schemas and behavior.

---

## 2. Database Models & Alembic Migration

### Data Models (`backend/app/models/tutor_session.py`)

#### `TutorThread`
Represents an ongoing conversational tutoring session.
- `id`: String(36), UUID primary key.
- `course_id`: String(36), foreign key to `courses.id` on delete CASCADE. Indexed.
- `student_id`: String(64), identifier of the student. Indexed.
- `title`: String(255), auto-derived from the initial question or user-specified.
- `created_at`: DateTime(timezone=True), creation timestamp.
- `updated_at`: DateTime(timezone=True), timestamp of most recent activity. Indexed.
- `messages`: Relationship to `TutorMessage`, cascade delete all orphans.

#### `TutorMessage`
Represents an individual message turn within a thread.
- `id`: String(36), UUID primary key.
- `thread_id`: String(36), foreign key to `tutor_threads.id` on delete CASCADE. Indexed.
- `role`: String(16), `'user'` or `'assistant'`.
- `content`: Text, message text.
- `status`: String(32), status tracking (`answered`, `out_of_scope`, `insufficient_evidence`, `no_course_material`).
- `citations_json`: JSON, serialized list of authentic content unit citations.
- `created_at`: DateTime(timezone=True), creation timestamp. Indexed.

### Migration
- **Revision ID:** `c7d3e5f1a805`
- **File:** `backend/alembic/versions/c7d3e5f1a805_add_tutor_threads_and_messages.py`
- **Down Revision:** `b8e4f2a1c099` (Milestone B6 BKT migration)
- **Features:** Standard foreign keys with `ON DELETE CASCADE`, composite and single indexes for query performance.

---

## 3. Conversational Context & Prompt Engineering

### Dynamic Context Query Builder
When follow-up questions rely on demonstrative pronouns (e.g., *"Can you explain step 2 again?"*, *"What about in the second case?"*), single-string semantic search might struggle. The engine constructs a contextual retrieval query by extracting the immediate preceding turn's core topic or combining recent questions:
```python
def build_contextual_retrieval_query(current_question: str, recent_history: List[TutorMessage]) -> str:
    # If the user question is short or anaphoric, blend in the previous user question
    ...
```

### Bounded Window History
Only the last $N$ messages (where $N=6$, equivalent to up to 3 conversational rounds) are formatted in chronological order:
```text
RECENT CONVERSATION HISTORY:
User: How does an AVL tree maintain balance?
Assistant: An AVL tree maintains balance using Left and Right rotations whenever the balance factor deviates from -1, 0, or +1.

CURRENT USER QUESTION:
Can you explain step 2 again?
```

### Grounding & Refusal Handling
The assistant prompt mandates that all claims must be grounded directly in the retrieved course excerpts. If an answer contains negative grounding markers (e.g. *"I could not find this information in the provided course material"*), the message status is marked as `insufficient_evidence` or `out_of_scope` and all citations are cleared.

---

## 4. API Endpoints

All thread endpoints are scoped under `/courses/{course_id}/tutor`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/courses/{course_id}/tutor/threads` | Create a new study conversation thread (custom or default title). |
| `GET` | `/courses/{course_id}/tutor/threads` | List all threads for a student in this course, ordered by latest update. |
| `GET` | `/courses/{course_id}/tutor/threads/{thread_id}` | Retrieve thread details including all historical messages & citations. |
| `DELETE`| `/courses/{course_id}/tutor/threads/{thread_id}` | Delete a thread and cascade delete all its messages. |
| `POST` | `/courses/{course_id}/tutor/threads/{thread_id}/messages`| Submit a user message and receive an assistant grounded response. |
| `POST` | `/courses/{course_id}/tutor/ask` | *(Unchanged)* Legacy single-turn tutor ask endpoint. |

### Sample Message Turn Request & Response

#### Request (`POST /courses/{course_id}/tutor/threads/{thread_id}/messages`)
```json
{
  "question": "Can you explain step 2 again?",
  "student_id": "alice",
  "top_k": 3
}
```

#### Response (`201 Created`)
```json
{
  "id": "7f8b9c2a-1122-3344-5566-778899aabbcc",
  "thread_id": "3e4f5a6b-7c8d-9e0f-1a2b-3c4d5e6f7a8b",
  "role": "assistant",
  "content": "Based on page 43 of Trees.pdf, Step 2 involves Left and Right Rotations to rebalance the AVL tree.",
  "status": "answered",
  "citations": [
    {
      "content_unit_id": "89ab12cd-34ef-5678-90ab-cdef12345678",
      "source_id": "fe123456-7890-abcd-ef01-234567890abc",
      "filename": "Trees.pdf",
      "page": 43,
      "score": 0.8842,
      "content_type": "pdf"
    }
  ],
  "created_at": "2026-10-11T17:52:00Z"
}
```

---

## 5. Verification & Test Suite

The test suite (`backend/test_b10_tutor_sessions.py`) validates:
1. **Thread Lifecycle**: Create (custom/default title), list, detail with messages, and deletion.
2. **Multi-Turn Context & Continuity**: Verify follow-up questions receive contextual history in the prompt.
3. **Citation Persistence**: Validate citation retention on historical messages across sessions.
4. **Sliding Window Boundaries**: Prove that long dialogues (10+ messages) strictly bound the LLM prompt to the most recent window.
5. **Grounding & Refusals**: Verify authentic citations on grounded answers and empty citations on refusals.
6. **Zero-Material Handling**: Verify immediate deterministic `no_course_material` responses without LLM dispatch.
7. **Student & Course Isolation**: Enforce strict 404 security boundaries across student IDs and course IDs.
8. **Cascading Deletion**: Deleting threads drops messages; deleting courses drops threads and messages.
9. **Backward Compatibility**: Confirm that `POST /courses/{course_id}/tutor/ask` continues to pass regression tests.

