# TESTING.md - 测试验收指南

本指南用于验证 Novel Polish 系统的核心功能链路，确保从配置到结果输出的闭环完整性。

## 🧪 1. LLM 连接链路验证 (Connectivity)
**目标**：验证 API Key 和协议路由是否正确。

- [ ] **OpenAI 兼容协议 (DeepSeek/SiliconFlow)**
  - 配置 `api: "openai"` $\rightarrow$ 点击 `测试连接` $\rightarrow$ 结果：`Success`
- [ ] **Anthropic 协议 (Claude)**
  - 配置 `api: "anthropic"` $\rightarrow$ 点击 `测试连接` $\rightarrow$ 结果：`Success`
- [ ] **Google 协议 (Gemini/Gemma)**
  - 配置 `api: "google"` $\rightarrow$ 模型名 `gemma-4-31b-it` $\rightarrow$ 点击 `测试连接` $\rightarrow$ 结果：`Success`
- [ ] **异常处理**
  - 输入错误的 API Key $\rightarrow$ 点击 `测试连接` $\rightarrow$ 结果：提示 `认证失败 (401)` 或相关错误

## 📏 2. 规则配置中心验证 (Rule Management)
**目标**：验证规则的持久化与结构完整性。

- [ ] **规则创建**：新建 `主类别` $\rightarrow$ `子类别` $\rightarrow$ `具体规则` $\rightarrow$ 点击保存 $\rightarrow$ 刷新页面 $\rightarrow$ 规则依然存在。
- [ ] **拖拽排序**：调整规则顺序 $\rightarrow$ 保存 $\rightarrow$ 验证顺序在 `rules.json` 中已更新。
- [ ] **状态切换**：禁用某个子类别 $\rightarrow$ 保存 $\rightarrow$ 启动润色 $\rightarrow$ 验证该类别下的规则未被应用。

## ✍️ 3. 核心润色流程验证 (End-to-End Polish)
**目标**：验证“文本 $\rightarrow$ 切片 $\rightarrow$ LLM $\rightarrow$ Diff”的全链路。

- [ ] **短文本测试**：输入 500 字以内文本 $\rightarrow$ 点击 `启动润色` $\rightarrow$ 结果：右侧出现 Diff 视图，且有实际修改。
- [ ] **长文本切片测试**：输入 5000 字以上文本 $\rightarrow$ 点击 `启动润色` $\rightarrow$ 观察 `日志面板` $\rightarrow$ 结果：看到 `Splitting text into X chunks` 且分块依次处理。
- [ ] **空输入测试**：不输入文本直接启动 $\rightarrow$ 结果：前端提示错误或后端返回 400，无崩溃。
- [ ] **并发压力测试**：连续快速点击 `启动润色` $\rightarrow$ 结果：系统应处理当前请求或正确跳过，无死锁。

## 📜 4. 历史记录与回溯验证 (History)
**目标**：验证 SQLite 数据库的存储与快照对比。

- [ ] **快照保存**：完成一次润色 $\rightarrow$ 进入 `历史记录` $\rightarrow$ 结果：出现一条带有时间戳的新记录。
- [ ] **版本对比**：点击历史记录中的某个版本 $\rightarrow$ 结果：工作台自动加载该版本的原始文本与润色结果。
- [ ] **记录删除**：删除某条历史 $\rightarrow$ 结果：列表立即更新，数据库中对应记录被移除。

## 🛠️ 5. 工业级健壮性验证 (Robustness)
**目标**：验证极端情况下的系统表现。

- [ ] **后端断开测试**：在润色过程中关闭后端进程 $\rightarrow$ 结果：前端 `日志面板` 显示 `Connection Lost` 并尝试自动重连。
- [ ] **API 限流测试**：使用低配 Key 触发 429 错误 $\rightarrow$ 结果：日志记录 `Rate Limited`，前端显示对应的错误提示。
- [ ] **配置动态刷新**：在 UI 修改模型 $\rightarrow$ 点击 `测试连接` $\rightarrow$ 立即启动润色 $\rightarrow$ 结果：无需重启后端即可使用新模型。

---

## 🏁 验收标准
- **P0 (必须通过)**: LLM 连接成功 $\rightarrow$ 文本能被润色 $\rightarrow$ 结果能正确显示在 Diff 视图。
- **P1 (重要)**: 规则配置可持久化 $\rightarrow$ 长文本能正确分块 $\rightarrow$ 历史记录可回溯。
- **P2 (优化)**: 实时日志流畅 $\rightarrow$ 错误提示友好 $\rightarrow$ 界面无明显卡顿。
