# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

Requires a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your_key_here
```

```bash
# Install dependencies
uv sync

# Start the server (PowerShell / any shell on Windows)
cd backend && uv run uvicorn app:app --reload --port 8000
```

App runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

Note: `main.py` at the project root is a placeholder and is not used. The real entry point is `backend/app.py`.

## Architecture

Full-stack RAG chatbot. The FastAPI backend serves both the API and the static frontend from `../frontend`. On startup, `app.py` loads all `.txt`/`.pdf`/`.docx` files from `../docs` into ChromaDB (skipping already-indexed courses by title).

### Component map

| File | Role |
|---|---|
| `backend/app.py` | FastAPI entry point; `/api/query` and `/api/courses` routes; startup document loader |
| `backend/rag_system.py` | Orchestrator — wires together all components; owns `query()` and `add_course_folder()` |
| `backend/ai_generator.py` | Claude API wrapper; implements the two-call tool-use pattern |
| `backend/search_tools.py` | `CourseSearchTool` (tool definition + execution) and `ToolManager` (registry/dispatcher) |
| `backend/vector_store.py` | ChromaDB wrapper; owns both collections and course-name resolution logic |
| `backend/document_processor.py` | Parses course files into `Course`/`Lesson`/`CourseChunk` objects and sentence-aware chunks |
| `backend/session_manager.py` | In-memory conversation history keyed by session ID |
| `backend/models.py` | Pydantic models: `Course`, `Lesson`, `CourseChunk` |
| `backend/config.py` | Single `Config` dataclass — all tuneable parameters |

### Query flow

1. Frontend (`frontend/script.js`) POSTs `{ query, session_id }` to `/api/query`
2. `app.py` creates a session if none exists, delegates to `RAGSystem.query()`
3. `RAGSystem` fetches conversation history (last 2 exchanges) and calls `AIGenerator`
4. `AIGenerator` makes a first Claude API call with the `search_course_content` tool available
5. If Claude calls the tool, `CourseSearchTool` runs a semantic search in ChromaDB and returns formatted chunks; Claude is called a second time (no tools) to synthesize the answer
6. Sources (`{label, url}` pairs) are pulled from `ToolManager.get_last_sources()` and reset
7. Session history is updated, then `answer` + `sources` + `session_id` are returned to the frontend, which renders Markdown and a collapsible sources panel

### Key design decisions

- **Two ChromaDB collections**: `course_catalog` stores course-level metadata (title, instructor, link, lessons serialized as JSON string); `course_content` stores text chunks with `course_title` and `lesson_number` metadata for filtering.
- **Course name resolution**: When the tool is called with a `course_name`, the vector store does a semantic search against `course_catalog` to find the best-matching title, then uses that exact title to filter `course_content`. This allows fuzzy course name matching.
- **Conversation history is injected into the system prompt** as a formatted string, not as separate messages in the `messages` array.
- **Tool execution is a two-call pattern**: first call may return `tool_use`; tool results are appended as a `user` message; second call (no tools) produces the final answer.
- **Sources are tracked as side-effects**: `CourseSearchTool` stores `last_sources` during result formatting; `ToolManager.get_last_sources()` collects them after the AI call completes, then `reset_sources()` clears them.

### Course document format

Files in `docs/` must follow this structure for proper parsing:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <title>
Lesson Link: <url>
<lesson content>

Lesson 2: <title>
...
```

`DocumentProcessor` chunks lesson content into ~800-character sentence-aware chunks with ~100-character overlap. The first chunk of each lesson is prefixed with `"Lesson N content: ..."` for retrieval context. If no `Lesson N:` markers are found, the entire file body is chunked as one block.

### Configuration

All tuneable parameters are in `backend/config.py`: model name, chunk size/overlap, max search results, conversation history length, ChromaDB path, and embedding model (`all-MiniLM-L6-v2`).
