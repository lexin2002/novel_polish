# AGENTS.md

## Dev Commands
- Frontend: `npm run dev` → http://localhost:5173
- Backend: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 57621`
- Both required simultaneously — Vite proxies `/api` and `/ws` to backend

## Verify
- **Order**: lint → type-check → test
- Single E2E: `npx playwright test tests/e2e/<file>.spec.ts`
- Backend: `cd backend && pytest tests/ -v`

## Architecture
- **Frontend**: React 18 + Vite + Tailwind + Zustand + Radix UI + dnd-kit
- **Backend**: FastAPI + Python 3.12 + aiosqlite + httpx
- **Electron**: `electron/main.ts`, `electron/preload.ts`
- **Path alias**: `@/*` → `src/*`

### Key Directories
- `src/` — React frontend
- `electron/` — Electron main/preload
- `backend/app/` — FastAPI (api/, core/, engine/)
- `backend/tests/` — pytest unit tests
- `tests/e2e/` — Playwright E2E tests

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
- Linux/macOS: `~/.config/NovelPolish/`
- Windows: `%APPDATA%/NovelPolish/`
- Files: `config.jsonc`, `rules.json`, `history.db`

## CI Build
- PyInstaller path: `app/main.py` (NOT `backend/app/main.py`)
- Output: `release/*.exe`

## Quirks
- Backend returns 503 if no API key configured (`/api/polish`)
- Config uses JSON5 (supports comments)
- E2E tests auto-start Vite via `playwright.config.ts` webServer
- Backend tests use `pytest-asyncio` + `pytest-cov`