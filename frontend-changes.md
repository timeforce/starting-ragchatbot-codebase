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
