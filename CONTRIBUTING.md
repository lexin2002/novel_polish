# Contributing to Novel Polish

Thank you for your interest in contributing to Novel Polish!

## 开发流程

### 1. Fork & Clone

```bash
git clone https://github.com/lexin2002/novel_polish.git
cd novel_polish
```

### 2. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 3. 开发与测试

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 运行测试
npm test

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

### 4. 提交更改

```bash
git add .
git commit -m "feat(scope): description of changes"
```

提交信息格式：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 其他更改

### 5. 推送并创建 PR

```bash
git push origin feature/your-feature-name
```

在 GitHub 上创建 Pull Request。

## 代码规范

### TypeScript

- 使用 strict TypeScript
- 避免使用 `any`
- 优先使用函数式组件和 Hooks
- 组件文件使用 PascalCase

### Python (Backend)

- 遵循 PEP 8
- 使用 type hints
- 使用 black 进行格式化
- 使用 flake8 进行 lint 检查

### Git 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

示例：
```
feat(rules): add drag-drop reordering for RuleEditor

- Implement @dnd-kit sortable for Category/SubCategory/Rule levels
- Add add/delete operations for all item types
- Update tests to cover new functionality

Closes #123
```

## 测试要求

### 前端 E2E 测试

所有 UI 功能必须通过 Playwright E2E 测试：

```bash
# 运行所有 E2E 测试
npm test

# 运行特定测试
npx playwright test tests/e2e/logPanel.spec.ts
```

### 后端单元测试

所有后端功能必须通过 pytest 测试：

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

覆盖率要求：≥80%

## 组件开发指南

### 创建新组件

1. 创建组件目录：`src/components/MyComponent/`
2. 实现组件：`MyComponent.tsx`
3. 导出组件：`index.ts`

```typescript
// src/components/MyComponent/MyComponent.tsx
import * as React from 'react'

interface MyComponentProps {
  title: string
}

export const MyComponent: React.FC<MyComponentProps> = ({ title }) => {
  return (
    <div className="p-4">
      <h2>{title}</h2>
    </div>
  )
}
```

### 创建 Zustand Store

```typescript
// src/store/myStore.ts
import { create } from 'zustand'

interface MyStore {
  data: string[]
  setData: (data: string[]) => void
}

export const useMyStore = create<MyStore>((set) => ({
  data: [],
  setData: (data) => set({ data }),
}))
```

### 创建 Hook

```typescript
// src/hooks/useMyHook.ts
import { useState, useEffect } from 'react'

export function useMyHook(param: string) {
  const [result, setResult] = useState<string>('')

  useEffect(() => {
    // 副作用逻辑
    setResult(param.toUpperCase())
  }, [param])

  return result
}
```

## API 开发指南

### REST API

在 `backend/app/api/rest.py` 中添加端点：

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/my-endpoint")
async def my_endpoint():
    return {"message": "Hello"}
```

### WebSocket

在 `backend/app/api/ws.py` 中添加处理器：

```python
async def websocket_handler(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 处理消息
    except WebSocketDisconnect:
        pass
```

## 遇到问题？

- 查看 [README.md](./README.md) 了解项目结构
- 查看现有测试了解测试模式
- 创建 Issue 进行问题反馈