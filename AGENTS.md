# AGENTS.md

## Dev Commands
- Frontend: `npm run dev` → http://localhost:5173
- Backend: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 57621`
- Both required simultaneously — Vite proxies `/api` and `/ws` to backend
- **Note**: LLM provider setup (API keys, models, etc.) is configured via the UI sidebar, NOT via `.env` file or scripts

## Verify
- **Order**: lint → type-check → test
- Backend: `cd backend && pytest tests/ -v --cov=app`

## Architecture
- **Frontend**: React 18 + Vite + Tailwind + Zustand + Radix UI + dnd-kit
- **Backend**: FastAPI + Python 3.12 + aiosqlite + httpx
- **Electron**: `electron/main.ts`, `electron/preload.ts`
- **Path alias**: `@/*` → `src/*`
- **Domain Model**: Rules use 3-level nesting: `MainCategory` → `SubCategory` → `Rule`

### Key Directories
- `src/` — React frontend
- `electron/` — Electron main/preload
- `backend/app/` — FastAPI (api/, core/, engine/)
- `backend/tests/` — pytest unit tests (46 tests)
- `backend/data/` — Runtime data (history.db, logs)

### Backend Entry Points
- `backend/app/main.py` — FastAPI app
- `backend/app/api/rest.py` — REST API
- `backend/app/api/ws.py` — WebSocket logs

## LLM Providers
| `api` value | Protocol | Endpoint |
|-------------|---------|----------|
| `openai` | OpenAI Chat Completions | `/v1/chat/completions` |
| `anthropic` | Anthropic Messages | `/v1/messages` |

DeepSeek, Qwen, SiliconFlow use `api: "openai"` (OpenAI-compatible)

## Config & Data
- **User config directory** (config.jsonc, rules.json): 
  - Linux/macOS: `~/.config/NovelPolish/`
  - Windows: `%APPDATA%/NovelPolish/`
- **Project data directory** (history.db, logs):
  - `backend/data/history.db` — SQLite database (history snapshots)
  - `backend/data/history/logs/` — Snapshot log files
- Files in user config: `config.jsonc`, `rules.json`
- Files in project data: `history.db`, `history/logs/`

## CI Build
- PyInstaller entry: `app/main.py` (relative to `backend/` directory, i.e. `backend/app/main.py`)
- Output: `release/*.exe`

## Quirks
- Backend returns 503 if no API key configured (`/api/polish`)
- Config uses JSON5 (supports comments)
- Backend tests use `pytest-asyncio` + `pytest-cov`
- `backend/app/core/history_db.py` uses absolute paths (`backend/data/`) instead of relative paths
- All LLM configuration (API keys, models, etc.) is managed via `config.jsonc` UI, NOT via `.env` file
