# Novel Polish - 小说智能润色工作台

A desktop-grade AI-powered novel writing assistant built with Electron + React + FastAPI.

## 🚀 快速开始

### 1. 环境要求
- Node.js 20+
- Python 3.12+
- npm 或 yarn

### 2. 安装依赖
```bash
# 前端依赖
npm install

# 后端依赖 (在 backend/ 目录下)
cd backend && pip install -r requirements.txt
```

### 3. 启动开发服务器
⚠️ **必须同时启动前端和后端**，Vite 会自动代理 `/api` 和 `/ws` 到后端。

#### 终端 1：启动后端 (FastAPI)
```bash
cd /home/wsl_lexin/novel_polish/backend
/home/wsl_lexin/novel_polish/backend/.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 57621
```

#### 终端 2：启动前端 (React + Vite)
```bash
cd /home/wsl_lexin/novel_polish
npm run dev -- --host 0.0.0.0
```

#### 验证访问
- **访问地址**: `http://localhost:5173`
- **验证链路**: `系统设置` $\rightarrow$ `配置 LLM` $\rightarrow$ `测试连接 (Success)` $\rightarrow$ `润色工作台` $\rightarrow$ `启动润色`

---

## 🛠️ 功能特性

- **智能润色**：基于 LLM 的小说文本分析与优化。
- **规则配置**：可定制的润色规则体系（主类别 $\rightarrow$ 子类别 $\rightarrow$ 规则）。
- **实时日志**：WebSocket 驱动的实时进度与日志监控。
- **历史管理**：快照历史记录与对比视图。
- **配置驾驶舱**：统一的可视化配置管理界面。

## 🏗️ 技术栈

### 前端
- **Electron** - 桌面应用框架
- **React 18** - UI 框架
- **Vite** - 构建工具
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式
- **Zustand** - 状态管理
- **Radix UI** - UI 组件库
- **@dnd-kit** - 拖拽排序

### 后端
- **FastAPI** - Web 框架
- **Python 3.12** - 运行环境
- **aiosqlite** - 异步数据库
- **filelock** - 文件锁
- **json5** - JSON 解析（支持注释）
- **Playwright** - E2E 测试
- **pytest** - 单元测试

---

## 📂 项目结构

```
novel_polish/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/
│   │   │   ├── rest.py         # REST API 端点
│   │   │   └── ws.py           # WebSocket 日志广播
│   │   ├── core/
│   │   │   ├── config_manager.py  # 配置管理（原子写入、多提供商）
│   │   │   ├── history_db.py      # 历史数据库 (backend/data/)
│   │   │   ├── llm_client.py      # 统一 LLM 客户端 (OpenAI/Anthropic/Google)
│   │   │   ├── rate_limiter.py    # 限流器
│   │   │   └── config.py          # 配置常量
│   │   ├── engine/                 # 润色引擎
│   │   │   ├── polishing_service.py  # 润色服务 (分块+并行+LLM调用)
│   │   │   ├── prompt_builder.py     # 提示构建
│   │   │   └── text_slicer.py        # 智能文本切片
│   │   ├── main.py               # 应用入口
│   │   └── __init__.py
│   ├── tests/                   # pytest 单元测试套件
│   │   ├── test_config_manager.py
│   │   │   └── ...
│   │   └── conftest.py
│   ├── data/                    # 运行时数据 (history.db + 日志)
│   └── requirements.txt         # Python 依赖清单
│
├── src/                        # React 前端源码
│   ├── components/             # UI 组件 (RuleEditor, LogPanel, Sidebar, Workbench)
│   ├── hooks/                  # 自定义 Hooks (useWebSocket)
│   ├── store/                  # Zustand 状态管理
│   ├── contexts/               # React 上下文 (WebSocketContext)
│   ├── App.tsx                # 主应用组件
│   └── main.tsx               # React 入口
│
├── electron/                   # Electron 主进程
│   ├── main.ts              # 主进程 (窗口管理 + 后端子进程)
│   └── preload.ts           # 预加载脚本
│
├── docs/                       # 专项文档
│   └── API.md               # 完整 API 参考
│
├── vite.config.ts               # Vite 构建 + API 代理
│
└── package.json                 # 前端依赖与脚本
```

## 🧪 测试指南

### 后端单元测试
```bash
cd /home/wsl_lexin/novel_polish/backend
/home/wsl_lexin/novel_polish/backend/.venv/bin/python3 -m pytest tests/ -v --cov=app
```

### 端到端测试
```bash
npm test
```

## 📋 LLM 协议支持

| `api` 值 | 协议标准 | 默认端点 | 适用模型 |
|---|---|---|---|
| `openai` | OpenAI Chat Completions | `/v1/chat/completions` | DeepSeek, SiliconFlow, Qwen, GPT |
| `anthropic` | Anthropic Messages | `/v1/messages` | Claude, DeepSeek (Anthropic 模式) |
| `google` | Google AI Studio | `/v1beta/models/{model}:generateContent` | Gemini, Gemma |

---

## 📄 许可证
MIT License
