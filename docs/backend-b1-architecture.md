# Phase B1 — Course Architecture & Database Foundation

**Status:** Completed & Verified  
**Branch:** `rudresh/backend-b1-database-foundation`  
**Base:** Phase B0 Baseline Checkpoint  

---

## 1. Overview & Architectural Role

Phase B1 introduces the persistent relational data layer and course/source abstractions for Edvora without modifying existing Phase 0 endpoints or breaking existing frontend contracts.

```mermaid
flowchart TD
    Client["Client / Frontend"] -->|REST /courses| FastAPI["FastAPI Application"]
    FastAPI -->|Request-scoped Dependency| get_db["get_db() Session Dependency"]
    get_db --> SessionLocal["SQLAlchemy SessionLocal"]
    SessionLocal --> Engine["SQLAlchemy Engine (pool_pre_ping=True)"]
    Engine --> Postgres[("Target: PostgreSQL / Test: SQLite")]

    subgraph Relational ORM Layer
        Course["Course Entity (UUID PK)"] -->|"1 : N (cascade='all, delete-orphan')"| Source["Source Entity (UUID PK, FK: course_id)"]
    end

    subgraph Migrations
        Alembic["Alembic Migrations"] -->|upgrade head| Schema["courses & sources tables"]
    end
```

---

## 2. Database Layer Implementation

### Engine & Session Management
- **File:** `backend/app/db/database.py`
- **Dialect / Target:** PostgreSQL (`postgresql://postgres:postgres@localhost:5432/edvora` by default from `DATABASE_URL`), with automatic SQLite fallback support for local isolated tests (`check_same_thread=False`).
- **Connection pooling:** `pool_pre_ping=True` ensures resilience against stale connections.
- **Dependency:** `get_db()` yields a request-scoped `Session` and guarantees `db.close()` in a `finally` block.
- **Environment:** Configured in `backend/.env.example` with safe placeholder documentation; `.env` is gitignored.

### Alembic Migrations
- **Environment Config:** `backend/alembic/env.py` dynamically loads `DATABASE_URL` from the application configuration and hooks into `Base.metadata`.
- **Initial Migration:** `backend/alembic/versions/d7f92aabd290_create_courses_and_sources_tables.py`
- **Tables created:**
  - `courses`
  - `sources`
- Verified bidirectional execution (`upgrade head` and `downgrade base`).

---

## 3. Data Models & Schemas

### `Course` Entity (`courses` table)
- `id`: String(36) UUID primary key (indexed).
- `title`: String(255) not nullable.
- `description`: Text nullable.
- `created_at`: DateTime(timezone=True) UTC.
- `updated_at`: DateTime(timezone=True) UTC.
- `sources`: Relationship to `Source`, configured with `cascade="all, delete-orphan"` and `passive_deletes=True`.

### `Source` Entity (`sources` table)
- `id`: String(36) UUID primary key (indexed).
- `course_id`: String(36) Foreign Key to `courses.id` on delete `CASCADE` (indexed).
- `filename`: String(255) not nullable.
- `source_type`: String(50) default `"pdf"`.
- `file_path`: String(500) nullable.
- `processing_status`: String(50) default `"pending"`.
- `created_at`: DateTime(timezone=True) UTC.
- `updated_at`: DateTime(timezone=True) UTC.
- `course`: Back-populates `Course`.

---

## 4. API Endpoints

Mounted via `backend/app/api/routes/course.py` into `backend/app/main.py`:

| Method | Endpoint | Description | Request Body | Response Status / Type |
|---|---|---|---|---|
| `POST` | `/courses` | Create a new course | `CourseCreate` (`title`, `description`) | `201 Created` (`CourseResponse`) |
| `GET` | `/courses` | List courses (paginated) | Query: `skip`, `limit` | `200 OK` (`CourseListResponse`) |
| `GET` | `/courses/{course_id}` | Get course by ID with sources | None | `200 OK` (`CourseResponse`) / `404` |
| `PUT` | `/courses/{course_id}` | Update course title/description | `CourseUpdate` | `200 OK` (`CourseResponse`) / `404` |
| `DELETE` | `/courses/{course_id}` | Delete course & cascade sources | None | `200 OK` (Confirmation message) / `404` |
| `POST` | `/courses/{course_id}/sources` | Add source to a course | `SourceCreate` | `201 Created` (`SourceResponse`) / `404` |
| `GET` | `/courses/{course_id}/sources` | List all sources for a course | None | `200 OK` (`List[SourceResponse]`) / `404` |
| `GET` | `/courses/{course_id}/sources/{source_id}` | Get specific source | None | `200 OK` (`SourceResponse`) / `404` |
| `DELETE` | `/courses/{course_id}/sources/{source_id}` | Delete a course source | None | `200 OK` (Confirmation message) / `404` |

---

## 5. Backward Compatibility & Preserved Guarantees

All Phase 0 endpoints and behavior remain unchanged and fully functional:
- `POST /documents/upload` — Ingests PDFs into in-memory store with page provenance.
- `POST /quiz/generate` — Grounded adaptive quiz generation.
- `POST /quiz/evaluate` — Stateless option evaluation.
- `POST /quiz/submit` — Multi-question submission with exact mastery calculation (no phantom increment).
- `POST /tutor/ask` — RAG tutor grounding; returns `sources: []` when ungrounded.
- `GET /recommendations/` — Returns weak concepts from learner model.
- `GET /health` & `GET /` — API liveness and status.

---

## 6. Verification Results

1. **B1 Isolated Test Suite (`backend/test_b1_courses.py`):**
   - `test_db_session_lifecycle`: PASSED
   - `test_course_and_source_models_cascade`: PASSED
   - `test_course_crud_endpoints`: PASSED
   - `test_course_source_endpoints`: PASSED
   - `test_preserved_phase0_endpoints`: PASSED
   - `test_alembic_migrations`: PASSED
   - Result: **6 passed in 0.56s**.

2. **Phase 0 Economics Regression Suite (`backend/test_phase0_economics.py`):**
   - 34-page PDF extraction + provenance: Verified
   - Topic & Concept extraction: Verified
   - Semantic retrieval: Verified
   - Tutor grounding + citation exactness: Verified
   - Negative grounding test (`sources: []`): Verified
   - Adaptive quiz generation + deduplication: Verified
   - Quiz evaluation & single-mutation mastery: Verified
   - Recommendations from learner state: Verified
   - Result: **All tests passed cleanly**.

3. **Frontend Health:**
   - `npm run lint` (`oxlint`): 0 warnings, 0 errors across 57 files.
   - `npm run build` (`vite build`): Succeeded cleanly (dist bundle built in 193ms).

---

## 7. Next Phase Scope (Phase B2)
The next phase (B2) will introduce:
- Persistent unified content model (`ContentUnit`).
- Persistent chunk storage with source/course foreign keys.
- Persistent vector retrieval / embeddings migration from the temporary in-memory store.

