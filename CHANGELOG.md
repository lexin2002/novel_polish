# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2026-04-25

### Added

#### Frontend
- **Electron + React + Vite scaffold** - Initial project setup with light theme configuration
- **RuleEditor component** - Tree-style rule configuration editor with:
  - Add/delete operations for Category, SubCategory, and Rule
  - Drag-drop reordering with @dnd-kit
  - Draft/original state management with priority validation
- **Sidebar component** - Config cockpit with Radix UI Accordion:
  - LLM configuration section
  - Engine performance parameters
  - Network request settings
  - UI behavior configuration
  - History management settings
- **LogPanel component** - Real-time terminal-style log viewer:
  - WebSocket connection with auto-reconnect
  - Color-coded log levels (INFO/WARN/ERROR)
  - Progress bar for chunk/iteration tracking
  - Pause and clear controls
- **useWebSocket hook** - Reusable WebSocket management with:
  - Auto-reconnect logic
  - Max 2000 log entries buffer
  - Progress event parsing
- **configStore** - Zustand store for config with debounced API sync
- **ruleStore** - Zustand store for rules with CRUD and validation

#### Backend
- **FastAPI REST API** - Endpoints for config, rules, and history management
- **WebSocket logging** - Real-time log broadcasting to connected clients
- **ConfigurationManager** - Atomic file persistence with FileLock for:
  - config.jsonc (with JSON5 support for comments)
  - rules.json
- **HistoryDatabase** - aiosqlite-based snapshot storage with auto-cleanup
  - **Updated**: Now uses absolute paths (`backend/data/`) instead of relative paths
  - Data directory: `backend/data/history.db`
  - Logs directory: `backend/data/history/logs/`
- **AsyncTokenBucket** - Rate limiting implementation
- **JitterDelay** - Random delay for API smoothing

#### Testing
- **Playwright E2E tests** - (Directory `tests/e2e/` does NOT exist currently)
  - App navigation and tab switching
  - Sidebar configuration interface
  - LogPanel visibility and controls
- **pytest unit tests** - (Directory `backend/tests/` has been deleted)
  - Originally 60+ tests with 85% coverage
  - Need to restore `backend/tests/` directory to run tests

### Features

- **Tab-based navigation**: Polish Workbench, Rules Center, History Archive, Config Cockpit
- **Real-time log monitoring**: WebSocket-driven with progress tracking
- **Rule configuration hierarchy**: MainCategory → SubCategory → Rule
- **Configuration persistence**: Atomic file writes with file locking
- **Debounced config sync**: 500ms debounce on config changes to reduce API calls

### Technical Stack

| Component | Technology |
|-----------|------------|
| Desktop Framework | Electron 28 |
| Frontend | React 18, TypeScript 5 |
| Build Tool | Vite 5 |
| State Management | Zustand 4 |
| UI Components | Radix UI, Lucide Icons |
| Drag & Drop | @dnd-kit |
| Backend | FastAPI, Python 3.12 |
| Database | aiosqlite |
| Testing | Playwright, pytest |

## [0.1.0] - 2026-04-24

### Added
- Initial project scaffolding
- Basic Electron + React setup
