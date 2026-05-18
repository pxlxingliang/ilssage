# A2A 多智能体通信设计

本文档详细描述 A2A 多智能体通信设计，对应主文档第 4.7 部分。

### 4.7 A2A 多智能体通信设计

A2A (Agent-to-Agent) 协议用于多智能体之间的任务分发与协作。

**A2A协议消息格式：** (详见 `backend/a2a/protocol.py`)

```
A2AMessage
  ├── message_id, from_agent, to_agent
  ├── message_type: "task" | "result" | "query" | "notify"
  ├── content, context, priority

A2ATask
  ├── task_id, description
  ├── required_skills, required_tools
  ├── status ("pending"), assigned_agent, result
```

**多智能体编排器：** (详见 `backend/a2a/orchestrator.py`)

```
AgentOrchestrator
  ├── register_agent(name, agent, capabilities)
  ├── decompose_and_dispatch(task_description, llm) → [A2ATask]
  │     // LLM 分解任务 → 按 capability 匹配 Agent → 分发
  └── execute_tasks(tasks) → {task_id: result}
        // 并发执行已分发的子任务，聚合结果
```
