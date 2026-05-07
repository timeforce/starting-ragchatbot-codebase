# Frontend-facing API Testing Infrastructure

## Changes Made

### New file: `backend/tests/test_api_endpoints.py`

12 tests covering the three endpoints the frontend communicates with:

**`POST /api/query`** (6 tests)
- Returns 200 with `answer`, `sources`, and `session_id` fields
- Auto-creates a session when `session_id` is omitted
- Reuses the provided `session_id` without calling `create_session`
- Forwards the query text to `RAGSystem.query()`
- Returns 500 when `RAGSystem.query()` raises
- Returns 422 when the required `query` field is missing

**`GET /api/courses`** (3 tests)
- Returns 200 with `total_courses` and `course_titles`
- Calls `get_course_analytics()` exactly once per request
- Returns 500 when `get_course_analytics()` raises

**`POST /api/session/clear`** (3 tests)
- Returns `{"status": "ok"}` on success and calls `clear_session` with the given ID
- Returns 500 when `clear_session()` raises
- Returns 422 when `session_id` is missing from the request body

### Updated: `backend/tests/conftest.py`

Two new shared fixtures added:

- **`mock_rag_system`** — a `MagicMock` replacing `RAGSystem` with pre-configured
  return values for `query`, `get_course_analytics`, and `session_manager.create_session`.
- **`test_client`** — creates a `fastapi.testclient.TestClient` against the real
  `app.py` FastAPI application, with two patches active:
  - `rag_system.RAGSystem` → `mock_rag_system` (no ChromaDB / Anthropic calls)
  - `fastapi.staticfiles.StaticFiles` → `_FakeStaticFiles` stub (no `../frontend`
    directory required)
  
  The `app` module is removed from `sys.modules` before each test and cleaned up
  after, ensuring each test gets a fresh import with the patches applied.

### Updated: `pyproject.toml`

- Added `httpx>=0.27.0` to `[project.optional-dependencies] dev` (required by
  Starlette's `TestClient` in FastAPI 0.116.1).
- Added `addopts = "-v --tb=short"` for verbose, readable test output.
- Added `filterwarnings` to suppress `DeprecationWarning` and
  `PendingDeprecationWarning` noise from transitive dependencies.
