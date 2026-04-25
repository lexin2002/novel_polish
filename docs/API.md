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

获取完整配置。

**Response**
```json
{
  "priority_order": ["P0", "P1", "P2", "P3"],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "",
    "base_url": "https://api.openai.com/v1",
    "temperature": 0.4,
    "max_tokens": 4096,
    "safety_exempt_enabled": true,
    "xml_tag_isolation_enabled": true,
    "desensitize_mode": false
  },
  "engine": {
    "chunk_size": 1000,
    "chunk_size_min": 500,
    "chunk_size_max": 3000,
    "max_workers": 3,
    "max_revisions": 2,
    "context_overlap_chars": 200,
    "context_snap_to_punctuation": true,
    "request_jitter_range": [0.2, 1.5],
    "max_requests_per_second": 2,
    "chunk_timeout_seconds": 60,
    "enable_invalid_modification_break": true
  },
  "network": {
    "request_timeout": 5,
    "retry_count": 3,
    "circuit_breaker_threshold": 3
  },
  "ui": {
    "log_to_file_enabled": true,
    "log_file_dir": "./logs",
    "experimental_realtime_log": false,
    "sync_scroll_default": false
  },
  "history": {
    "max_snapshots": 20
  }
}
```

---

### Update Configuration

**PATCH** `/api/config`

部分更新配置（支持嵌套键）。

**Request Body**
```json
{
  "llm": {
    "temperature": 0.6,
    "model": "gpt-4-turbo"
  }
}
```

**Response** - 返回完整更新后的配置

---

### Get Configuration Paths

**GET** `/api/config/path`

获取配置文件路径。

**Response**
```json
{
  "config": "/path/to/config.jsonc",
  "rules": "/path/to/rules.json"
}
```

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
              "instruction": "将'在'改为'再'当表示重复时...",
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

### Get History

**GET** `/api/history`

获取历史快照列表（按时间倒序）。

**Query Parameters**
- `limit` (optional, default: 20) - 返回数量上限

**Response**
```json
[
  {
    "id": 1,
    "created_at": "2026-04-25T22:00:00",
    "content_preview": "这是一段小说文本的预览...",
    "rules_applied": ["P0-语法与标点", "P1-逻辑一致性"],
    "modifications_count": 15
  }
]
```

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

获取指定快照详情。

**Response**
```json
{
  "id": 1,
  "created_at": "2026-04-25T22:00:00",
  "original_content": "原始文本...",
  "polished_content": "润色后文本...",
  "rules_applied": ["P0-语法与标点"],
  "modifications": [
    {
      "rule": "常见形近字错误",
      "before": "在",
      "after": "再",
      "position": {"line": 5, "char": 10}
    }
  ]
}
```

---

### Delete History

**DELETE** `/api/history/{snapshot_id}`

删除指定快照。

**Response**
```json
{
  "status": "ok",
  "message": "Snapshot deleted"
}
```

---

## WebSocket API

### Log Streaming

**WS** `/ws/logs`

WebSocket 端点，用于实时日志流。

**连接**

```javascript
const ws = new WebSocket('ws://localhost:57621/ws/logs')

ws.onopen = () => {
  console.log('Connected to log stream')
  ws.send('ping') // 心跳保活
}

ws.onmessage = (event) => {
  const data = event.data
  // 处理日志或进度消息
}
```

**日志消息格式**

后端发送的日志格式：
```
2026-04-25 22:00:00 - INFO - 开始处理文本块 1/5
2026-04-25 22:00:01 - WARN - 检测到可能的重复词汇
2026-04-25 22:00:02 - ERROR - 连接超时，重试中...
```

**进度消息格式**

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

**Ping/Pong**

客户端可发送 `ping` 消息，服务端会回复 `pong`。

---

## 错误响应

所有 API 错误遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：
- `200` - 成功
- `400` - 请求参数错误
- `404` - 资源不存在
- `500` - 服务器内部错误

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

### ConfigState

```typescript
interface ConfigState {
  priority_order: string[]
  llm: {
    provider: string
    model: string
    api_key: string
    base_url: string
    temperature: number
    max_tokens: number
    safety_exempt_enabled: boolean
    xml_tag_isolation_enabled: boolean
    desensitize_mode: boolean
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