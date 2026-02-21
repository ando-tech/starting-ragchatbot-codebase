# Frontend Changes: Dark/Light Theme Toggle

## Summary
Added a dark/light theme toggle button to the RAG Chatbot UI. Users can switch between the existing dark theme and a new light theme. The preference is persisted in `localStorage` and the system color-scheme preference is respected on first visit.

---

## Files Modified

### `frontend/index.html`

1. **Inline theme script in `<head>`** — Added a small inline `<script>` block that reads `localStorage` (or falls back to `prefers-color-scheme`) and sets `data-theme` on `<html>` before the page renders. This prevents a flash of the wrong theme on page load.

2. **Theme toggle button** — Added a `<button id="themeToggle" class="theme-toggle">` element just before the closing `</body>` tag. It contains two SVG icons:
   - **Sun icon** (`.sun-icon`) — visible in dark mode; clicking switches to light.
   - **Moon icon** (`.moon-icon`) — visible in light mode; clicking switches to dark.
   - Both icons carry `aria-hidden="true"`; the button itself has `aria-label="Toggle theme"` and `title` for accessibility/tooltip.

---

### `frontend/style.css`

1. **New CSS variables in `:root`**
   - `--error-color: #f87171` — replaces the hardcoded error text color.
   - `--success-color: #4ade80` — replaces the hardcoded success text color.

2. **Light theme block** — Added `[data-theme="light"]` selector that overrides all relevant CSS custom properties:
   | Variable | Dark (default) | Light |
   |---|---|---|
   | `--background` | `#0f172a` | `#f8fafc` |
   | `--surface` | `#1e293b` | `#ffffff` |
   | `--surface-hover` | `#334155` | `#f1f5f9` |
   | `--text-primary` | `#f1f5f9` | `#0f172a` |
   | `--text-secondary` | `#94a3b8` | `#64748b` |
   | `--border-color` | `#334155` | `#e2e8f0` |
   | `--shadow` | `rgba(0,0,0,0.3)` | `rgba(0,0,0,0.1)` |
   | `--focus-ring` | `rgba(37,99,235,0.2)` | `rgba(37,99,235,0.15)` |
   | `--welcome-bg` | `#1e3a5f` | `#eff6ff` |
   | `--error-color` | `#f87171` | `#dc2626` |
   | `--success-color` | `#4ade80` | `#16a34a` |

3. **Smooth theme transitions** — Added a rule targeting key layout and content elements (`body`, `.sidebar`, `.chat-messages`, `.message-content`, `.stat-item`, `.source-pill`, etc.) to transition `background-color`, `color`, and `border-color` over `0.3s ease` when the theme switches.

4. **Error/success message colors** — Updated `.error-message` and `.success-message` to use `var(--error-color)` and `var(--success-color)` respectively, so they adapt correctly between themes.

5. **`.theme-toggle` button styles**
   - `position: fixed; top: 1rem; right: 1rem; z-index: 1000` — always visible in the top-right corner.
   - Circular (`border-radius: 50%`), 40×40 px.
   - Uses `--surface`, `--border-color`, `--text-secondary` so it blends with the current theme.
   - Hover: scales up slightly (`transform: scale(1.08)`) and shifts to `--surface-hover`.
   - Focus: visible ring using `--focus-ring` (accessible keyboard navigation).
   - Icon swap: `.sun-icon` and `.moon-icon` are `position: absolute` inside the button. CSS opacity and rotation transitions (`0.3s ease`) handle the animated icon crossfade:
     - Dark mode → sun visible, moon hidden.
     - Light mode → moon visible, sun hidden.

---

### `frontend/script.js`

1. **`initTheme()` function** — Reads `localStorage.getItem('theme')` and falls back to `prefers-color-scheme` media query. Sets `data-theme` on `document.documentElement` (`<html>`). Called at the top of `DOMContentLoaded` (the inline head script also runs earlier to prevent flash).

2. **`toggleTheme()` function** — Reads the current `data-theme` attribute, toggles between `'dark'` and `'light'`, updates `document.documentElement`, and persists to `localStorage`.

3. **Event listener** — Wired up in `setupEventListeners()`:
   ```js
   document.getElementById('themeToggle').addEventListener('click', toggleTheme);
   ```

---

## Design Decisions

- **CSS custom properties** — All colors are already driven by CSS variables in `:root`. The light theme only needs to override those variables; no element-level styles were duplicated.
- **`data-theme` on `<html>`** — Placing the attribute on the root element means a single CSS selector (`[data-theme="light"]`) cascades to the entire page without specificity conflicts.
- **No flash** — The inline `<script>` in `<head>` sets the theme attribute synchronously before first paint, so users never see a flash of the wrong theme.
- **Persistence + system preference** — `localStorage` takes priority; new visitors get the theme that matches their OS setting.
- **Accessibility** — Button has `aria-label`, SVGs are `aria-hidden`, and focus styling uses a visible ring matching the existing design language.
