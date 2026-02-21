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

---

# Frontend Changes: Code Quality Tooling

## Feature: Frontend Code Quality Tooling

Added essential code quality tools and formatting consistency for the frontend (JS, CSS, HTML).

---

### New Files

#### `package.json`
- Introduces a minimal Node.js dev-tooling manifest (private, no publishing).
- **Dev dependencies**: `prettier@^3`, `eslint@^9`, `@eslint/js@^9`.
- **npm scripts**:
  - `npm run format` — format all `frontend/**` files in-place with Prettier.
  - `npm run format:check` — verify formatting without writing changes (CI-safe).
  - `npm run lint` — run ESLint on `frontend/`.
  - `npm run quality` — run both `format:check` and `lint` in sequence.

#### `.prettierrc`
Prettier configuration tuned to the existing frontend style:
| Option | Value | Reason |
|---|---|---|
| `semi` | `true` | Existing JS uses semicolons |
| `singleQuote` | `true` | Existing JS uses single quotes |
| `tabWidth` | `4` | Existing JS/CSS/HTML uses 4-space indent |
| `printWidth` | `100` | Allows readable lines without over-wrapping |
| `trailingComma` | `"es5"` | Safer ES5-compatible trailing commas |
| `endOfLine` | `"lf"` | Consistent line endings across platforms |

#### `eslint.config.js`
ESLint flat config (ESLint 9+ format) for `frontend/**/*.js`:
- Extends `@eslint/js` recommended rules.
- Declares browser globals (`document`, `window`, `fetch`, `marked`, etc.) so ESLint does not flag them as undefined.
- Custom rules:
  - `no-unused-vars` → **warn** (catch dead code without blocking)
  - `no-console` → **warn** (clean up debug logs before merging)
  - `eqeqeq` → **error** (enforce strict equality)
  - `no-var` → **error** (ban legacy `var` declarations)
  - `prefer-const` → **warn** (encourage immutable bindings)

#### `scripts/format-frontend.sh`
Shell script that runs `npx prettier --write` on all frontend files. Useful as a one-shot fix before committing.

```bash
./scripts/format-frontend.sh
```

#### `scripts/check-frontend.sh`
Shell script that runs both Prettier (check mode) and ESLint, prints a summary, and exits non-zero if anything fails. Suitable for use in CI or pre-commit hooks.

```bash
./scripts/check-frontend.sh
```

---

### Modified Files

#### `frontend/script.js`
- **Broke up long `addMessage(...)` call** in `createNewSession()` (line 197): the single-argument call with a 150+ character string literal was split onto multiple lines to stay within the 100-character print width.
- **Removed extra blank line** between `setupEventListeners()` and the `// Chat Functions` comment block (was two blank lines, now one).

#### `frontend/index.html`
- **Removed extra blank line** before the `<script>` tags at the bottom of `<body>` (was two blank lines, now one).

---

### Usage

```bash
# Install dev dependencies (one-time)
npm install

# Check formatting and lint (does not modify files)
npm run quality
# or
./scripts/check-frontend.sh

# Auto-fix formatting
npm run format
# or
./scripts/format-frontend.sh

# Lint only
npm run lint
```
