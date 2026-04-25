# Task Context: Stage 1 - Scaffold & Backend Core

Session ID: 2026-04-25-stage1-scaffold-and-backend
Created: 2026-04-25T00:00:00
Status: in_progress

## Current Request
Implement two development shards:
1. Frontend scaffold validation + light theme config + E2E tests
2. Python FastAPI backend with health check + WebSocket logger

## Context Files (Standards to Follow)
No context files exist yet - using project conventions and requirements from the development plan document.

## Reference Files (Source Material to Look At)
- package.json - NPM dependencies and scripts
- tailwind.config.js - existing theme colors (light theme: bg #f9f9f9, text #1a1a1a, border #e0e0e0)
- vite.config.ts - Vite + Electron plugin config
- electron/main.ts - Electron main process
- electron/preload.ts - Preload bridge
- tests/e2e/app.spec.ts - existing Playwright E2E tests
- src/App.tsx - Main React component

## External Docs Fetched
None required for this stage.

## Components
1. **Shard 1 - Frontend Scaffold**: Validate existing setup, verify Tailwind light theme, ensure E2E tests pass
2. **Shard 2 - Backend Core**: Create FastAPI backend with REST health endpoint + WebSocket logger on port 57621

## Constraints
- Port 57621 is locked for backend
- Light theme colors: background #f9f9f9, foreground #1a1a1a, border #e0e0e0
- Frontend uses: React 18 + TypeScript + Vite + Tailwind CSS + Electron
- Backend uses: Python FastAPI + uvicorn
- E2E testing: Playwright for frontend, Pytest for backend

## Exit Criteria
- [ ] Frontend: npm run lint && npm run type-check passes
- [ ] Frontend: npx playwright test passes (all E2E tests)
- [ ] Backend: GET /api/health returns {"status": "ok"}
- [ ] Backend: WS /ws/logs broadcasts log messages
- [ ] Backend: Pytest tests pass with >90% coverage