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
