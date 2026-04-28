# AGENTS.md

## 🚀 快速启动 (Quick Start)

### 1. 启动后端 (Backend)
后端运行在 `57621` 端口，负责 API 逻辑和 LLM 调度。
```bash
cd /home/wsl_lexin/novel_polish/backend
/home/wsl_lexin/novel_polish/backend/.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 57621
```

### 2. 启动前端 (Frontend)
前端运行在 `5173` 端口，通过 Vite 代理将 `/api` 和 `/ws` 转发至后端。
```bash
cd /home/wsl_lexin/novel_polish
npm run dev -- --host 0.0.0.0
```

### 3. 验证流程 (Verification)
- **访问地址**: `http://localhost:5173`
- **基本链路**: `系统设置` $\rightarrow$ `配置 LLM` $\rightarrow$ `测试连接 (Success)` $\rightarrow$ `润色工作台` $\rightarrow$ `输入文本` $\rightarrow$ `启动润色` $\rightarrow$ `查看 Diff 结果`
- **日志监控**: 点击界面右上角 `> 日志` 按钮查看实时后端输出。

---

## 🛠️ 开发与验证 (Dev & Verify)

### 自动化测试
- **顺序**: lint $\rightarrow$ type-check $\rightarrow$ test
- **后端测试**: 
  ```bash
  cd /home/wsl_lexin/novel_polish/backend
  /home/wsl_lexin/novel_polish/backend/.venv/bin/python3 -m pytest tests/ -v --cov=app
  ```

### 架构概览
- **Frontend**: React 18 + Vite + Tailwind + Zustand + Radix UI + dnd-kit
- **Backend**: FastAPI + Python 3.12 + aiosqlite + httpx
- **Electron**: `electron/main.ts`, `electron/preload.ts`
- **Domain Model**: 规则采用三级嵌套：`MainCategory` $\rightarrow$ `SubCategory` $\rightarrow$ `Rule`

### 核心目录
- `src/` — React 前端源代码
- `electron/` — Electron 主进程与预加载脚本
- `backend/app/` — FastAPI 核心逻辑 (api/, core/, engine/)
- `backend/tests/` — pytest 单元测试与模拟测试
- `backend/data/` — 运行时数据 (history.db, logs)

### LLM 协议支持
| `api` 值 | 协议标准 | 默认端点 | 适用模型 |
|---|---|---|---|
| `openai` | OpenAI Chat Completions | `/v1/chat/completions` | DeepSeek, SiliconFlow, Qwen, GPT |
| `anthropic` | Anthropic Messages | `/v1/messages` | Claude, DeepSeek (Anthropic 模式) |
| `google` | Google AI Studio | `/v1beta/models/{model}:generateContent` | Gemini, Gemma |

---

## 📂 配置与数据 (Config & Data)

### 用户配置路径
- **Linux/macOS**: `~/.config/NovelPolish/` (`config.jsonc`, `rules.json`)
- **Windows**: `%APPDATA%/NovelPolish/`

### 项目数据路径
- **SQLite 数据库**: `backend/data/history.db`
- **快照日志**: `backend/data/history/logs/`

### 关键特性 (Quirks)
- **动态配置**: 所有 LLM 配置通过 `config.jsonc` UI 管理，无需修改 `.env`。
- **JSON5 支持**: 配置文件支持注释，使用 `json5` 解析。
- **路径硬编码**: `backend/app/core/history_db.py` 使用绝对路径 `backend/data/` 以保证稳定性。
- **错误响应**: 若未配置 API Key，`/api/polish` 将返回 `503 Service Unavailable`。
