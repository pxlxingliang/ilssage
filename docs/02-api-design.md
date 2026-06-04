# API设计

本文档详细描述 ILsSage 智能体框架的 API 设计内容，对应主文档的第 5 部分。

## 5. API设计

### 5.1 RESTful API

```
# LLM管理
GET    /api/v1/llm/providers            # 获取所有LLM提供商
GET    /api/v1/llm/models               # 获取所有模型
POST   /api/v1/llm/switch              # 切换当前模型
GET    /api/v1/llm/current             # 获取当前使用的模型
GET    /api/v1/llm/models/{id}/info    # 获取特定模型信息

# 会话管理
GET    /api/v1/sessions                 # 获取会话列表
POST   /api/v1/sessions                 # 创建新会话
GET    /api/v1/sessions/{id}            # 获取特定会话（含消息）
PUT    /api/v1/sessions/{id}            # 更新会话（标题、模型等）
DELETE /api/v1/sessions/{id}            # 删除会话
POST   /api/v1/sessions/{id}/switch-model  # 切换会话模型

# 聊天交互
POST   /api/v1/chat/{session_id}/send          # 发送消息（非流式）
POST   /api/v1/chat/{session_id}/stream        # 发送消息（SSE流式）
GET    /api/v1/chat/{session_id}/history       # 获取聊天历史
POST   /api/v1/chat/{session_id}/cancel        # 取消当前生成
POST   /api/v1/chat/{session_id}/pause         # 暂停执行（保存检查点）
POST   /api/v1/chat/{session_id}/resume        # 从检查点恢复

# MCP工具管理
GET    /api/v1/mcp/servers              # 获取MCP服务器列表
POST   /api/v1/mcp/servers/connect      # 连接MCP服务器
POST   /api/v1/mcp/servers/disconnect   # 断开MCP服务器
GET    /api/v1/mcp/tools                # 获取所有可用MCP工具
GET    /api/v1/mcp/tools/{name}         # 获取特定工具信息
POST   /api/v1/mcp/tools/{name}/execute # 直接执行工具（调试用）

# Skill管理
GET    /api/v1/skills                   # 获取所有Skill列表

# 记忆管理
GET    /api/v1/memory/long-term         # 获取长期记忆
POST   /api/v1/memory/long-term         # 添加长期记忆
DELETE /api/v1/memory/long-term/{id}    # 删除长期记忆
POST   /api/v1/memory/search            # 语义搜索历史对话
POST   /api/v1/memory/summarize         # 生成对话摘要

# Agent评估
POST   /api/v1/eval/run                 # 运行评估任务
GET    /api/v1/eval/results/{task_id}   # 获取评估结果
GET    /api/v1/eval/metrics             # 获取全局指标统计

# 工作区/上下文
GET    /api/v1/workspace/context        # 获取当前工作区上下文
PUT    /api/v1/workspace/file/{name}    # 更新上下文文件（AGENT.md等）
```

### 5.2 WebSocket API & SSE

框架同时支持 WebSocket（首选）和 SSE（降级 fallback）。

**WebSocket API:**
```
WebSocket: /api/v1/ws/chat?session_id={id}&token={token}

# 客户端 → 服务器
{
  "type": "message",
  "content": "你好"
}

# 客户端 → 服务器（取消生成）
{
  "type": "cancel"
}

# 服务器 → 客户端（推理/思考过程）
{
  "type": "thinking",
  "content": "让我分析一下这个问题..."
}

# 服务器 → 客户端（流式内容）
{
  "type": "content",
  "content": "好的，我来帮你"
}

# 服务器 → 客户端（工具调用开始）
{
  "type": "tool_call_start",
  "tool_name": "read_file",
  "tool_args": {"file_path": "main.py"},
  "display_args": {"file_path": "main.py"}
}

# 服务器 → 客户端（工具调用完成）
{
  "type": "tool_call_end",
  "tool_name": "read_file",
  "result": "import os\n...",
  "duration_ms": 234,
  "is_error": false
}

# 服务器 → 客户端（完成）
{
  "type": "done",
  "message_id": "msg_xyz789",
  "total_tokens": 1234,
  "tool_calls": 3,
  "metrics": {"steps": 3, "time_s": 5.2}
}

# 服务器 → 客户端（错误）
{
  "type": "error",
  "code": "RATE_LIMITED",
  "message": "请求过于频繁，请稍后重试"
}
```

**SSE 降级方案（当 WebSocket 不可用）：**
```
POST /api/v1/chat/{session_id}/stream

Response (text/event-stream):
event: thinking
data: {"content": "让我思考一下..."}

event: content
data: {"content": "你好"}

event: tool_call_start
data: {"tool_name": "read_file", "args": {...}}

event: tool_call_end
data: {"tool_name": "read_file", "result": "...", "duration_ms": 234}

event: done
data: {"message_id": "msg_xyz", "total_tokens": 1234}
```

---

