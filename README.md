# Novel Polish - 小说智能润色工作台

A desktop-grade AI-powered novel writing assistant built with Electron + React + FastAPI.

## 功能特性

- **智能润色**：基于 LLM 的小说文本分析与优化
- **规则配置**：可定制的润色规则体系（主类别 → 子类别 → 规则）
- **实时日志**：WebSocket 驱动的实时进度与日志监控
- **历史管理**：快照历史记录与对比
- **配置驾驶舱**：统一的可视化配置管理

## 技术栈

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

## 项目结构

```
novel_polish/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/
│   │   │   ├── rest.py         # REST API 端点
│   │   │   └── ws.py           # WebSocket 日志广播
│   │   ├── core/
│   │   │   ├── config_manager.py  # 配置管理（原子写入、多提供商）
│   │   │   ├── history_db.py      # 历史数据库（数据在 backend/data/）
│   │   │   ├── llm_client.py      # 统一 LLM 客户端（OpenAI/Anthropic）
│   │   │   ├── rate_limiter.py    # 限流器
│   │   │   └── config.py          # 配置常量
│   │   ├── engine/                 # 润色引擎
│   │   │   ├── polishing_service.py  # 润色服务（分块+并行+LLM调用）
│   │   │   ├── prompt_builder.py     # 提示构建（XML隔离+安全豁免）
│   │   │   └── text_slicer.py        # 智能文本切片（标点吸附+上下文重叠）
│   │   ├── main.py               # 应用入口
│   │   └── __init__.py
│   ├── tests/                   # pytest 单元测试套件（46 个测试）
│   │   ├── test_config_manager.py
│   │   ├── test_prompt_builder.py
│   │   ├── test_text_slicer.py
│   │   └── conftest.py
│   ├── data/                    # 运行时数据（history.db + 日志）
│   └── requirements.txt         # Python 依赖清单
│
├── src/                        # React 前端源码
│   ├── components/
│   │   ├── RuleEditor/        # 规则配置编辑器（拖拽排序）
│   │   ├── LogPanel/          # 实时日志面板（WebSocket 驱动）
│   │   ├── Sidebar/            # 配置驾驶舱（LLM/引擎/网络/UI）
│   │   ├── Workbench/          # 润色工作台（Monaco DiffEditor）
│   │   └── shared/             # 共享组件（ProgressBar）
│   ├── hooks/
│   │   └── useWebSocket.ts     # WebSocket Hook（自动重连）
│   ├── store/
│   │   ├── configStore.ts      # 配置状态管理（debounced 同步）
│   │   └── ruleStore.ts        # 规则状态管理（CRUD + dnd-kit）
│   ├── contexts/
│   │   └── WebSocketContext.tsx  # WebSocket 上下文
│   ├── App.tsx                # 主应用组件（标签页导航）
│   └── main.tsx               # React 入口
│
├── electron/                   # Electron 主进程
│   ├── main.ts              # 主进程（窗口管理 + 后端子进程）
│   └── preload.ts           # 预加载脚本（contextBridge API）
├── docs/                       # 专项文档
│   └── API.md               # 完整 API 参考（14 个端点）
├── vite.config.ts               # Vite 构建 + Electron 插件 + API 代理
├── package.json                 # 前端依赖与脚本
├── tsconfig.json                # TypeScript 配置
└── .env.example                 # 环境变量说明（仅 PORT/HOST）
```

## 快速开始

### 环境要求
- Node.js 20+（推荐，Electron 28 需要）
- Python 3.12+
- npm 或 yarn

### 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖（在 backend/ 目录下）
cd backend && pip install -r requirements.txt
```

### 启动开发服务器

⚠️ **必须同时启动前端和后端**，两个服务都需要运行（Vite 会自动代理 `/api` 和 `/ws` 到后端）

```bash
# 终端1：启动前端 (Vite dev server，默认 http://localhost:5173)
npm run dev

# 终端2：启动后端 (FastAPI，端口 57621，开发模式建议加 --reload)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 57621 --reload
```

### 运行测试

```bash
# 端到端测试（35 个测试覆盖全部 4 个 Tab 页交互）
npm test

# 后端单元测试（46 个测试覆盖 Config/规则/Prompt/文本切片）
cd backend && pytest tests/ -v --cov=app
```

## API 端点

### REST API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/config` | 获取完整配置 |
| PATCH | `/api/config` | 部分更新配置（支持嵌套路径） |
| POST | `/api/config` | 全量替换配置 |
| POST | `/api/config/reset` | 重置为默认配置 |
| GET | `/api/config/path` | 获取配置文件路径（调试用） |
| POST | `/api/config/test-connection` | 测试 LLM API 连接 |
| GET | `/api/rules` | 获取规则 |
| POST | `/api/rules` | 保存规则 |
| POST | `/api/polish` | 润色文本（核心功能） |
| GET | `/api/history` | 获取历史记录列表 |
| GET | `/api/history/count` | 获取历史记录数量 |
| GET | `/api/history/{id}` | 获取指定历史记录详情 |
| DELETE | `/api/history/{id}` | 删除历史记录 |

### WebSocket

| 路径 | 描述 |
|------|------|
| `/ws/logs` | 实时日志流 |

## 配置说明

### 配置文件位置
- **Linux/macOS**: `~/.config/NovelPolish/config.jsonc`
- **Windows**: `%APPDATA%/NovelPolish/config.jsonc`
- 规则文件：同上目录下的 `rules.json`
- 历史数据库（后端数据目录）：`backend/data/history.db`（默认位置，由 `backend/app/core/history_db.py` 管理）
- 历史日志目录：`backend/data/history/logs/`

### LLM 配置结构

LLM 配置采用**以提供商为中心**的结构，支持多提供商切换：

```json
{
  "llm": {
    "active_provider": "openai",
    "temperature": 0.4,
    "max_tokens": 4096,
    "safety_exempt_enabled": true,
    "xml_tag_isolation_enabled": true,
    "desensitize_mode": false,
    "providers": {
      "openai": {
        "name": "OpenAI",
        "api": "openai",
        "api_key": "sk-...",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "active_model": "gpt-4o"
      },
      "anthropic": {
        "name": "Anthropic",
        "api": "anthropic",
        "api_key": "sk-ant-...",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-5-sonnet-latest", "claude-3-opus-latest", "claude-3-haiku-latest"],
        "active_model": "claude-3-5-sonnet-latest"
      },
      "deepseek": {
        "name": "DeepSeek",
        "api": "openai",
        "api_key": "sk-...",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"],
        "active_model": "deepseek-chat"
      },
      "qwen": {
        "name": "通义千问",
        "api": "openai",
        "api_key": "sk-...",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
        "active_model": "qwen-turbo"
      },
      "siliconflow": {
        "name": "SiliconFlow",
        "api": "openai",
        "api_key": "sk-...",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["THUDM/GLM-4-32B-0414", "Qwen/Qwen2-72B-Instruct", "deepseek-ai/DeepSeek-V2.5"],
        "active_model": "THUDM/GLM-4-32B-0414"
      },
      "custom": {
        "name": "自定义",
        "api": "openai",
        "api_key": "sk-...",
        "base_url": "",
        "models": [],
        "active_model": ""
      }
    }
  },
  "engine": { ... },
  "network": { ... },
  "ui": { ... },
  "history": { ... }
}
```

### API 类型说明

每个提供商都有 `api` 字段，决定使用哪种 API 协议：

| api 值 | 说明 | 使用的 API 端点 |
|--------|------|----------------|
| `openai` | OpenAI 兼容协议（Chat Completions） | `/v1/chat/completions` |
| `anthropic` | Anthropic 协议（Messages） | `/v1/messages` |

**重要**: `api` 字段控制实际使用的协议，**不是**提供商名称。例如：
- OpenAI 必须使用 `api: "openai"`
- Anthropic 必须使用 `api: "anthropic"`
- DeepSeek/Qwen/SiliconFlow 使用 `api: "openai"`（它们是 OpenAI 兼容 API）

### 测试 LLM 连接

在 UI 中配置完成后，可以点击"测试连接"按钮验证 API Key 和配置是否正确。

也可以通过 API 测试：

```bash
curl -X POST http://localhost:57621/api/config/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "active_provider": "openai",
    "providers": {
      "openai": {
        "api": "openai",
        "api_key": "your-key-here",
        "base_url": "https://api.openai.com/v1",
        "active_model": "gpt-4o"
      }
    }
  }'
```

成功返回：`{"ok": true, "model": "gpt-4o", "response": "OK"}`
失败返回：`{"ok": false, "error": "认证失败: API Key 无效或已过期 (401)"}`

## 规则配置

规则采用三级嵌套结构：

```
主类别 (MainCategory)
  └── 子类别 (SubCategory)
        └── 规则 (Rule)
```

### 规则结构

```typescript
interface Rule {
  name: string           // 规则名称
  is_active: boolean     // 是否启用
  instruction: string    // 修改指令
  direction?: string     // 审查方向
}

interface SubCategory {
  name: string
  priority: string       // P0, P1, P2, P3...
  rules: Rule[]
}

interface MainCategory {
  name: string
  priority: string
  is_active: boolean
  sub_categories: SubCategory[]
}
```

## 开发指南

### 添加新的 UI 组件

1. 在 `src/components/` 下创建组件目录
2. 实现组件并导出
3. 在 `App.tsx` 中引入使用

### 添加 API 端点

1. 在 `backend/app/api/rest.py` 中添加路由
2. 使用 `ConfigurationManager` 进行配置持久化
3. 使用 `HistoryDatabase` 进行数据存储

### 测试

```bash
# 端到端测试（Playwright，35 个测试覆盖全部 Tab 页）
npm test

# 后端单元测试（46 个测试）
cd backend && pytest tests/ -v --cov=app
```

## 构建发布

```bash
# 构建前端和 Electron
npm run build
```

构建产物位于 `release/` 目录。

## 许可证

MIT License