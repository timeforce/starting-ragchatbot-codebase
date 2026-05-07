# Frontend Changes: Dark / Light Theme Toggle

## Summary

Added a theme toggle button that lets users switch between the existing dark theme and a new light theme. The chosen theme is persisted in `localStorage` so it survives page refreshes.

---

## Files Changed

### `frontend/index.html`

1. **Inline theme-init script in `<head>`** — reads `localStorage` and sets `data-theme` on `<html>` *before* first paint, preventing any flash of wrong theme.
2. **Theme toggle `<button>`** — fixed-position button with two SVG icons (sun and moon) placed just before `</body>`. Uses `aria-label` and `title` for accessibility; fully keyboard-navigable.
3. Bumped stylesheet cache-buster from `v=10` → `v=11` and script from `v=9` → `v=10`.

### `frontend/style.css`

1. **New CSS variables on `:root`** — converted previously hardcoded `rgba(...)` and hex values to variables so they respond to theme switches:
   - `--code-bg` — inline code / pre block background
   - `--source-pill-bg`, `--source-pill-border`, `--source-pill-color` — source chip default state
   - `--source-pill-hover-bg`, `--source-pill-hover-border`, `--source-pill-hover-color` — source chip hover state
   - `--sources-divider` — thin rule above the sources collapsible

2. **`[data-theme="light"]` block** — overrides every relevant variable with light-theme values:
   - `--background: #f8fafc`, `--surface: #ffffff`, `--surface-hover: #f1f5f9`
   - `--text-primary: #0f172a`, `--text-secondary: #64748b`, `--border-color: #e2e8f0`
   - `--code-bg: rgba(0,0,0,0.05)` — subtler in light mode
   - Source pill / hover variables switched to blue-tinted values for legibility on white

3. **Smooth transition rule** — added `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` to structural elements (`body`, `.sidebar`, `.chat-main`, `.chat-container`, `.chat-messages`, `.message-content`, `.chat-input-container`, `.stat-item`) so theme changes animate instead of cutting.

4. **`.theme-toggle` button styles** — circular 40×40 px button, `position: fixed; top: 1rem; right: 1rem; z-index: 200`. Hover scales up with a blue glow; focus shows the existing `--focus-ring` outline.

5. **Icon visibility rules** — in dark mode the sun icon is shown (click → go light); in `[data-theme="light"]` the moon icon is shown (click → go dark). Controlled purely with CSS `display` toggling.

6. Updated `.sources-collapsible`, `.source-pill`, `a.source-pill:hover`, `.message-content code`, and `.message-content pre` to use the new CSS variables instead of the previous hardcoded rgba strings.

### `frontend/script.js`

1. Added `themeToggle` to the DOM-element declarations.
2. Wired `toggleTheme` to the button's `click` event inside `setupEventListeners()`.
3. Added `toggleTheme()` function — reads current `data-theme` from `<html>`, flips to the opposite value, writes it back to the element, and persists it in `localStorage`.

---

## Design Decisions

- **`data-theme` on `<html>`** — placing the attribute on the root element lets both `:root` variable blocks and descendant CSS selectors (`[data-theme="light"] .theme-toggle …`) resolve cleanly with a single attribute write.
- **No JS for icon switching** — icon visibility is handled entirely in CSS (`[data-theme="light"] .icon-sun { display: none }`), keeping the JS minimal.
- **Inline init script** — the synchronous snippet in `<head>` applies the theme before any element is rendered, eliminating the dark-to-light flash that would occur if the JS ran after `DOMContentLoaded`.
- **Selective transitions** — transitions are applied only to structural/container elements, not to all `*`, to avoid interfering with existing hover/focus/active transitions on interactive controls.

---

# Frontend Quality Tools — Changes

## What was added

### Prettier (code formatter)

- `frontend/.prettierrc` — config: 2-space indentation, single quotes, semicolons, ES5 trailing commas, 80-char print width
- `frontend/.prettierignore` — excludes `node_modules/` and `*.min.js`

### ESLint (linter)

- `frontend/.eslintrc.json` — `eslint:recommended` base, browser + ES2021 env, `marked` declared as a read-only global, `prefer-const` and `no-var` enforced as errors

### Package

- `frontend/package.json` — dev dependencies for `prettier@^3.3.0` and `eslint@^8.57.0`; npm scripts:
  - `npm run format` — auto-format all frontend files
  - `npm run format:check` — CI-safe check (exit 1 on diff)
  - `npm run lint` — lint `script.js`
  - `npm run check` — runs format:check then lint

### Dev script

- `scripts/check-frontend.ps1` — PowerShell wrapper that runs Prettier check then ESLint; pass `-Fix` to auto-format instead of just checking

## Files reformatted

All three source files were reformatted to match the Prettier config (4-space → 2-space indentation throughout, trailing commas in JS objects/arrays, self-closing void elements and multi-line attribute wrapping in HTML):

- `frontend/script.js`
- `frontend/index.html`
- `frontend/style.css`

### Notable style changes in each file

**script.js**
- Indentation: 4 spaces → 2 spaces
- Arrow-function parameters now parenthesised: `e =>` → `(e) =>`
- Trailing commas added to multi-line object/array literals
- Long `addMessage(...)` call in `createNewSession` split across lines to stay within 80 chars
- Removed stale comments that described what the code does rather than why

**index.html**
- Doctype lowercased: `<!DOCTYPE html>` → `<!doctype html>`
- Indentation: 4 spaces → 2 spaces
- Void elements self-closed: `<meta ...>` → `<meta ... />`
- Long `<button data-question="...">` attributes split to one-per-line

**style.css**
- Indentation: 4 spaces → 2 spaces
- Universal selector split to one-per-line: `*, *::before, *::after` → separate lines
- `transition` shorthand with multiple values split to multi-line (Prettier CSS style)
- `@keyframes bounce` percentage selectors grouped on one line: `0%, 80%, 100%`
- Removed inline comment inside `.course-titles` that restated what `max-height: none` means

## How to use

```powershell
# Install dev tools (one-time, from frontend/)
cd frontend
npm install

# Check formatting + lint
npm run check

# Auto-fix formatting
npm run format

# Or use the project-level script from the repo root
.\scripts\check-frontend.ps1          # check only
.\scripts\check-frontend.ps1 -Fix     # auto-format
```

---

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
