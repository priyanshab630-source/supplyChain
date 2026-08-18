# frontend/

## Why this exists
A Vite + React chat UI for the supply-chain assistant. Talks to
`backend/`'s FastAPI service only — it has no direct database or
LangGraph access. Its entire job is: send a question, stream the
response, render each agent's progress as it arrives.

## Folders
| Folder | Purpose |
|---|---|
| `src/` | All application code — see `src/README.md` |
| `public/` | Static assets served as-is by Vite |
| `node_modules/` | Installed dependencies (not committed) |

## Root Files
| File | What it does |
|---|---|
| `vite.config.js` | Vite dev server + build configuration |
| `index.html` | HTML entry point Vite injects the bundled app into |
| `package.json` / `package-lock.json` | Dependencies and scripts (`npm run dev`, `npm run build`) |
| `eslint.config.js` | Lint rules |
| `.gitignore` | Excludes `node_modules/`, build output, `.env` |

## Environment
Reads `VITE_API_BASE` (falls back to `http://localhost:8000/api` if
unset) — see `src/api/README.md`. Set this in a `.env` file at this
folder's root if your backend isn't running on the default port/host.

## Run
```bash
npm install
npm run dev
```
Requires `backend/` running separately (see the root `README.md` for
full setup order) — the frontend has nothing to render until it can
reach `POST /api/threads` on startup.
