# Agent核心设计

本文档详细描述 Agent核心设计，对应主文档第 4.8 部分。

### 4.8 Agent核心设计

**Agent基类：** (详见 `backend/core/agent.py`)

```
BaseAgent (ABC)
  ├── 属性: provider (LLMProvider), system_prompt, tools (ToolRegistry)
  ├── 状态机: IDLE → RUNNING → PAUSED / ERROR → IDLE
  │
  ├── run(messages) → str                    // 抽象：同步运行
  ├── stream_run(messages) → AsyncIterator   // 抽象：流式运行
  ├── cancel()                               // 中断当前执行
  ├── pause() / resume()                     // 暂停/恢复（保存检查点）
```

**SimpleAgent：** (详见 `backend/agents/simple_agent.py`)

```
SimpleAgent(BaseAgent)
  // 纯 LLM 透传，无工具调用
  run(messages) → str        // 构建 system prompt + history → provider.ainvoke → 返回
  stream_run(messages) → y   // 同上但流式 (provider.astream_invoke)
```

**ReActAgent：** (详见 `backend/agents/react_agent.py`)

```
ReActAgent(BaseAgent)       // 实际使用的 Agent，基于 OpenAI tool-calling
  run(messages):
    loop:
      调用 LLM (带 tools schema)
      if LLM 返回 tool_calls:
        执行每个 tool_call → 追加 assistant/tool 消息 → 继续循环
      else:
        返回文本内容 → 结束
  stream_run(messages):
    同上，但流式产出 AgentEvent (content_chunk | tool_call_start | tool_call_end | done)
```

**ReflectionAgent / PlanSolveAgent：** (详见 `backend/agents/reflection_agent.py`, `plan_solve_agent.py`)
当前为 stub（`raise NotImplementedError`），留待后续实现。

**事件系统：** (详见 `backend/core/events.py`)

```
AgentEventType enum: CONTENT_CHUNK | REASONING_CHUNK | TOOL_CALL_START | TOOL_CALL_END | DONE | ERROR
AgentEvent: {type, data} → to_dict() | to_sse() | to_json()
```
