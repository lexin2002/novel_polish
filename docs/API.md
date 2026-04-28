# API Documentation

Novel Polish 后端 API 文档。

## Base URL

```
http://localhost:57621
```

## REST API

### Health Check

**GET** `/api/health`

检查服务健康状态。

**Response**
```json
{
  "status": "ok"
}
```

---

### Get Configuration

**GET** `/api/config`

获取完整配置（包含所有提供商的配置）。

**Response** — 返回完整配置对象，包含 `llm`, `engine`, `network`, `ui`, `history`, `priority_order` 等所有章节。

---

### Update Configuration (Partial)

**PATCH** `/api/config`

部分更新配置（支持嵌套路径）。可更新特定提供商的配置，或切换活动提供商。深层合并请求体到现有配置中。

**Request Body** — 任意配置子集，支持嵌套合并。

```json
{
  "llm": {
    "active_provider": "anthropic",
    "temperature": 0.6,
    "providers": {
      "anthropic": {
        "api_key": "sk-ant-...",
        "active_model": "claude-3-5-sonnet-latest"
      }
    }
  }
}
```

**Response** — 返回完整更新后的配置。

**可能的错误**
- `409 Conflict` — 配置文件被锁定（FileLock 超时导致只读模式）

---

### Replace Configuration (Full)

**POST** `/api/config`

全量替换当前配置。请求体会完全替代现有配置，未提供的字段将使用默认值填充。

**Request Body** — 完整的 ConfigState JSON 对象（可选部分字段，缺失字段会从默认配置补全）。

**Response**
```json
{
  "status": "ok",
  "message": "Config written successfully"
}
```

**可能的错误**
- `409 Conflict` — 配置文件被锁定（只读模式），需稍后重试

---

### Reset Configuration

**POST** `/api/config/reset`

重置配置为默认值。

**Response**
```json
{
  "status": "ok",
  "message": "Config reset to defaults"
}
```

---

### Get Config File Paths

**GET** `/api/config/path`

获取配置文件和规则文件的磁盘绝对路径（调试用）。

**Response**
```json
{
  "config": "/home/user/.config/NovelPolish/config.jsonc",
  "rules": "/home/user/.config/NovelPolish/rules.json"
}
```

---

### Test LLM Connection

**POST** `/api/config/test-connection`

测试 LLM API 连接是否可用。后端会根据请求体中的配置创建临时 LLM 客户端并发起测试请求。

**Request Body** — LLM 配置的 `llm` 章节：

```json
{
  "active_provider": "openai",
  "providers": {
    "openai": {
      "api": "openai",
      "api_key": "sk-...",
      "base_url": "https://api.openai.com/v1",
      "active_model": "gpt-4o"
    }
  }
}
```

**Response (成功)**
```json
{
  "ok": true,
  "model": "gpt-4o",
  "response": "OK"
}
```

**Response (失败)**
```json
{
  "ok": false,
  "error": "认证失败: API Key 无效或已过期 (401)"
}
```

**常见错误类型**

| 错误信息 | 说明 |
|---------|------|
| `API Key 不能为空` | 未提供 API Key |
| `Base URL 不能为空` | 未提供 Base URL |
| `请先选择一个模型` | 未选择模型 |
| `Provider xxx not found in config` | 指定的活动提供商 ID 不存在于 providers 中 |
| `认证失败: API Key 无效或已过期 (401)` | API Key 错误（来自 LLM 服务） |
| `访问被拒绝: 权限不足 (403)` | 账户权限不足（来自 LLM 服务） |
| `模型不存在或端点错误: xxx (404)` | 模型名称错误或不支持（来自 LLM 服务） |
| `请求频率超限，请稍后重试 (429)` | 请求过于频繁（来自 LLM 服务） |
| `网络连接失败: xxx` | 网络问题 |

> **注意**：401/403/404/429 等状态码来自 LLM 远端服务（OpenAI/Anthropic 等），后端本身无认证机制。

---

### Get Rules

**GET** `/api/rules`

获取规则配置。

**Response**
```json
{
  "main_categories": [
    {
      "name": "语法与标点",
      "priority": "P0",
      "is_active": true,
      "sub_categories": [
        {
          "name": "错别字",
          "priority": "P0",
          "rules": [
            {
              "name": "常见形近字错误",
              "is_active": true,
              "instruction": "将"在"改为"再"当表示重复时；将"的"改为"地"当修饰动词时。",
              "direction": "诊断并修改"
            }
          ]
        }
      ]
    }
  ]
}
```

---

### Save Rules

**POST** `/api/rules`

完整替换规则配置。

**Request Body**
```json
{
  "main_categories": [...]
}
```

**Response**
```json
{
  "status": "ok",
  "message": "Rules updated successfully"
}
```

---

### Polish Text

**POST** `/api/polish`

使用 LLM 对小说文本进行智能润色。文本会被自动分块并行处理，支持进度追踪（通过 WebSocket）。

**Request Body**
```json
{
  "text": "要润色的小说文本...",
  "rules_state": null,
  "enable_safety_exempt": true,
  "enable_xml_isolation": true
}
```

**参数说明**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | 是 | — | 小说文本，长度 1 ~ 100000 字符 |
| `rules_state` | object | 否 | null | 规则配置（含 main_categories），为空时使用当前已保存规则 |
| `enable_safety_exempt` | boolean | 否 | true | 是否注入小说写作安全豁免声明 |
| `enable_xml_isolation` | boolean | 否 | true | 是否将用户文本包裹在 XML 隔离标签中 |

**Response（成功）**
```json
{
  "original_text": "原始文本...",
  "polished_text": "润色后的文本...",
  "modifications": [],
  "chunks_processed": 3,
  "total_tokens": 1500
}
```

**Response（失败 - 503）**
```json
{
  "detail": "Polishing service not initialized"
}
```

**可能的错误**
- `503 Service Unavailable` — 润色服务未初始化（未配置 API Key）
- `500 Internal Server Error` — 润色过程出错（具体信息见 detail 字段）

---

### Get History

**GET** `/api/history?limit=20`

获取历史快照列表（按时间倒序）。每条快照包含原文和润色后文本的预览。

**Query Parameters**
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | integer | 20 | 返回数量上限 |

**Response**
```json
[
  {
    "id": 1,
    "timestamp": "2026-04-25T22:00:00",
    "original_text": "原始文本...",
    "revised_text": "润色后文本...",
    "log_file_path": "/path/to/backend/data/history/logs/snapshot_...log",
    "chunk_params": {
      "chunk_size": 1000,
      "overlap": 200
    }
  }
]
```

**字段说明**
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 快照唯一 ID |
| `timestamp` | string (ISO 8601) | 创建时间 |
| `original_text` | string | 原始文本 |
| `revised_text` | string | 润色后文本 |
| `log_file_path` | string 或 null | 关联的日志文件路径（若有） |
| `chunk_params` | object 或 null | 分块参数（若有） |

---

### Get History Count

**GET** `/api/history/count`

获取历史快照总数。

**Response**
```json
{
  "count": 42
}
```

---

### Get History Detail

**GET** `/api/history/{snapshot_id}`

获取指定快照的完整详情，包含规则快照和配置快照。

**Response**
```json
{
  "id": 1,
  "timestamp": "2026-04-25T22:00:00",
  "original_text": "原始文本...",
  "revised_text": "润色后文本...",
  "rules_snapshot": {
    "main_categories": [...]
  },
  "config_snapshot": {
    "llm": {...},
    "engine": {...}
  },
  "log_file_path": "/path/to/log/file.log",
  "chunk_params": null
}
```

**字段说明**
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 快照唯一 ID |
| `timestamp` | string (ISO 8601) | 创建时间 |
| `original_text` | string | 原始文本（完整） |
| `revised_text` | string | 润色后文本（完整） |
| `rules_snapshot` | object | 润色时使用的规则配置快照 |
| `config_snapshot` | object | 润色时使用的系统配置快照 |
| `log_file_path` | string 或 null | 关联的日志文件路径（若有） |
| `chunk_params` | object 或 null | 分块参数（若有） |

**可能的错误**
- `404 Not Found` — 指定的 snapshot_id 不存在

---

### Delete History

**DELETE** `/api/history/{snapshot_id}`

删除指定快照及其关联的日志文件。

**Response**
```json
{
  "status": "ok",
  "message": "Snapshot deleted"
}
```

**可能的错误**
- `404 Not Found` — 指定的 snapshot_id 不存在

---

## WebSocket API

### Log Streaming

**WS** `/ws/logs`

WebSocket 端点，用于实时日志流。广播后端运行时的日志、进度状态等信息。

**连接**

```javascript
// 推荐使用相对路径以兼容不同部署环境
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`)
```

**日志消息格式**

后端发送的日志使用标准 logging 格式：
```
2026-04-25 22:00:00 - INFO - 开始处理文本块 1/5
2026-04-25 22:00:01 - WARN - 检测到可能的重复词汇
2026-04-25 22:00:02 - ERROR - 连接超时，重试中...
```

**进度消息格式**（JSON 格式日志）

```json
{
  "type": "progress",
  "data": {
    "chunk": 2,
    "total_chunks": 5,
    "iteration": 3,
    "total_iterations": 4,
    "message": "正在处理块 2，迭代 3"
  }
}
```

**连接心跳**

客户端可发送 `ping` 消息保持连接活跃，服务端会回复 `pong`。

```javascript
ws.send('ping')
```

**重连机制**

前端 `useWebSocket` hook 内置自动重连，断线后每 3 秒尝试重新连接。

---

## 错误响应

所有 API 错误遵循 FastAPI 标准格式：

```json
{
  "detail": "错误描述信息"
}
```

### 常见 HTTP 状态码

| 状态码 | 含义 | 常见场景 |
|--------|------|----------|
| `200` | 成功 | 请求正常处理 |
| `400` | 请求参数错误 | 请求体格式错误 |
| `404` | 资源不存在 | 历史快照 ID 不存在 |
| `409` | 资源冲突 | 配置文件被锁定，暂时只读 |
| `500` | 服务器内部错误 | 润色过程中 LLM 调用失败 |
| `503` | 服务不可用 | 未配置 API Key 时访问 `/api/polish` |

> 注意：401 Unauthorized 和 403 Forbidden 等认证错误由 LLM 远端服务返回，并非后端自身认证。后端目前无认证机制。

---

## 数据类型

### Priority

优先级字符串，可选值：`P0`, `P1`, `P2`, `P3`, `P4`, `P5`

### Rule

```typescript
interface Rule {
  name: string           // 规则名称
  is_active: boolean     // 是否启用
  instruction: string    // 修改指令（精确描述如何修改）
  direction?: string     // 审查方向（如"诊断并修改"）
}
```

### SubCategory

```typescript
interface SubCategory {
  name: string
  priority: string
  rules: Rule[]
}
```

### MainCategory

```typescript
interface MainCategory {
  name: string
  priority: string
  is_active: boolean
  sub_categories: SubCategory[]
}
```

### RulesState

```typescript
interface RulesState {
  main_categories: MainCategory[]
}
```

### ProviderConfig

```typescript
interface ProviderConfig {
  name: string              // 显示名称，如 "OpenAI"
  api: "openai" | "anthropic"  // API 协议类型
  api_key: string           // API 密钥
  base_url: string          // API 端点基础 URL
  models: string[]           // 可用模型列表
  active_model: string       // 当前选中的模型
}
```

### ConfigState

```typescript
interface ConfigState {
  priority_order: string[]
  llm: {
    active_provider: string                        // 当前活动的提供商 ID
    temperature: number
    max_tokens: number
    safety_exempt_enabled: boolean
    xml_tag_isolation_enabled: boolean
    desensitize_mode: boolean
    providers: Record<string, ProviderConfig>        // 所有提供商的配置
  }
  engine: {
    chunk_size: number
    chunk_size_min: number
    chunk_size_max: number
    max_workers: number
    max_revisions: number
    context_overlap_chars: number
    context_snap_to_punctuation: boolean
    request_jitter_range: [number, number]
    max_requests_per_second: number
    chunk_timeout_seconds: number
    enable_invalid_modification_break: boolean
  }
  network: {
    request_timeout: number
    retry_count: number
    circuit_breaker_threshold: number
  }
  ui: {
    log_to_file_enabled: boolean
    log_file_dir: string
    experimental_realtime_log: boolean
    sync_scroll_default: boolean
  }
  history: {
    max_snapshots: number
  }
}
```
