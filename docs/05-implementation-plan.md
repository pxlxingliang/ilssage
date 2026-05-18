# 已实现的交互增强

本文档详细描述在原始设计方案基础上新增的交互功能，对应主文档的第10部分。

## 10. 已实现的交互增强

以下为在原始设计方案基础上新增的交互功能：

### 10.1 Token 计数与展示

- **预调用计数**：发送前使用 `tiktoken`（OpenAI 模型精确编码）或字符估算（fallback）计算 prompt token 数
- **API 用量捕获**：通过 `stream_options={"include_usage": True}` 捕获流式响应中的 `prompt_tokens` / `completion_tokens` / `total_tokens`；非流式调用从 `response.usage` 获取
- **Web 端展示**：输入框下方实时显示 `~N tokens`；回复完成后在助手消息底部显示用量明细（`1,234 prompt + 256 completion = 1,490 total`）
- **TUI 端展示**：状态栏发送前显示 `tokens: N/128K`，发送后显示 `tokens: N prompt + M completion = T`
- **相关文件**：`backend/core/token_counter.py`（新增）、`backend/core/llm.py`、`backend/agents/react_agent.py`、`backend/tui/screen.py`、`frontend/src/components/ChatPanel/index.tsx`

### 10.2 消息元数据持久化（Token 用量 + 工具调用）

- `SessionService.add_message()` 新增 `metadata` 可选参数，写入 JSON 文件中的消息条目
- 助手回复保存时附带 `metadata.token_usage`，前端加载历史时恢复 token 显示
- 前端 `buildMessagesFromApi()` 纯函数统一处理历史加载：文本 + tool_calls（先文字后卡片），与 streaming 路径的穿插渲染解耦
- **相关文件**：`backend/services/session_service.py`、`backend/api/routes/chat.py`、`backend/tui/screen.py`、`frontend/src/components/ChatPanel/index.tsx`

### 10.3 流式输出中止保护

- **Web 端**：点击停止按钮后，已接收的 `streamingSegments` 立即 flush 为 assistant 消息并附加 `*(输出被用户截断)*` 标记（不再丢失）
- **后端 SSE**：`generate()` 协程用 `finally` 块在连接断开（`asyncio.CancelledError`）时自动保存部分内容
- **WebSocket**：streaming 放入独立 `asyncio.Task`，主循环可接收 cancel 消息；部分内容附截断标记保存
- **TUI 端**：1.5s 内连按两次 <kbd>Esc</kbd> 停止输出；第一次按时状态栏提示 `Press Esc again to stop`；取消后保存部分内容 + 截断标记
- **相关文件**：`backend/api/routes/chat.py`、`backend/api/routes/ws.py`、`backend/tui/screen.py`、`frontend/src/components/ChatPanel/index.tsx`

### 10.4 请求队列（防止并发输出）

- **Web 端**：`send()` 拆分为 `send()`（分流）+ `doStream()`（实际 SSE 请求）+ `flushQueue()`（消费队列）；streaming 期间新消息入队，自动提示 `等待前面的任务完成...`，当前回复完成后自动消费下一条
- **TUI 端**：`_streaming` 期间新消息入 `_pending_messages` 队列，状态栏显示 `N task(s) queued...`，当前 worker 结束后自动启动下一个
- **相关文件**：`backend/tui/screen.py`、`frontend/src/components/ChatPanel/index.tsx`
