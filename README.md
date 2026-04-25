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
- **Playwright** - E2E 测试

### 后端
- **FastAPI** - Web 框架
- **Python 3.12** - 运行环境
- **aiosqlite** - 异步数据库
- **filelock** - 文件锁
- **json5** - JSON 解析（支持注释）
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
│   │   │   ├── config_manager.py  # 配置管理（原子写入）
│   │   │   ├── history_db.py      # 历史数据库
│   │   │   ├── rate_limiter.py     # 限流器
│   │   │   └── config.py           # 配置常量
│   │   └── main.py             # 应用入口
│   └── tests/                  # pytest 测试
│
├── src/                        # React 前端源码
│   ├── components/
│   │   ├── RuleEditor/        # 规则配置编辑器
│   │   ├── LogPanel/          # 实时日志面板
│   │   └── Sidebar/            # 配置驾驶舱
│   ├── hooks/
│   │   └── useWebSocket.ts    # WebSocket Hook
│   ├── store/
│   │   ├── configStore.ts      # 配置状态管理
│   │   └── ruleStore.ts        # 规则状态管理
│   ├── App.tsx                # 应用入口
│   └── main.tsx                # React 入口
│
├── tests/e2e/                  # Playwright E2E 测试
├── electron/                  # Electron 主进程
└── package.json
```

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.12+
- npm 或 yarn

### 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖
cd backend
pip install -r requirements.txt
```

### 启动开发服务器

```bash
# 启动前端 (Vite dev server)
npm run dev

# 启动后端 (另一个终端)
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 57621
```

### 运行测试

```bash
# 前端 E2E 测试
npm test

# 后端单元测试
cd backend
pytest tests/ -v
```

## API 端点

### REST API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/config` | 获取配置 |
| PATCH | `/api/config` | 更新配置 |
| GET | `/api/rules` | 获取规则 |
| POST | `/api/rules` | 保存规则 |
| GET | `/api/history` | 获取历史记录 |
| DELETE | `/api/history/{id}` | 删除历史记录 |

### WebSocket

| 路径 | 描述 |
|------|------|
| `/ws/logs` | 实时日志流 |

## 配置说明

### 配置文件位置
- 配置文件：`backend/data/config.jsonc`
- 规则文件：`backend/data/rules.json`
- 历史数据库：`backend/data/history.db`

### 配置结构

```json
{
  "priority_order": ["P0", "P1", "P2", "P3"],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "",
    "base_url": "https://api.openai.com/v1",
    "temperature": 0.4,
    "max_tokens": 4096
  },
  "engine": {
    "chunk_size": 1000,
    "max_workers": 3,
    "max_revisions": 2
  },
  "network": {
    "request_timeout": 5,
    "retry_count": 3
  },
  "ui": {
    "log_to_file_enabled": true,
    "sync_scroll_default": false
  },
  "history": {
    "max_snapshots": 20
  }
}
```

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
# 运行所有测试
npm test

# 运行特定测试文件
npx playwright test tests/e2e/logPanel.spec.ts

# 运行后端测试
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