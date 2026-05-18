# 异步工具执行器设计

本文档详细描述 异步工具执行器设计，对应主文档第 4.9 部分。

### 4.9 异步工具执行器设计

**工具权限分级：** (详见 `backend/tools/permission.py`)

```
ToolPermission: READ_ONLY | WRITE | EXECUTE | NETWORK
  // 四级权限：只读 < 写入 < 网络 < 执行
```

**异步执行器：** (详见 `backend/tools/async_executor.py`)

```
AsyncToolExecutor
  ├── register_tool_config(name, timeout, retries, permission)
  ├── execute(tool_name, tool_fn, args) → result
  │     // 带超时控制 + 自动重试 + 信号量并发限制
  └── cancel(tool_name)  // 取消正在执行的任务

当前状态: async_executor.py + permission.py 尚未实现（空文件）
```

### 4.10 Agent评估体系设计

**运行指标：** (详见 `backend/evaluation/metrics.py`)

```
AgentMetrics: task_id, success, steps_taken, tools_called, total_time, llm_calls, total_tokens, errors
```

**评估器：** (详见 `backend/evaluation/`)

```
AgentEvaluator
  ├── evaluate(metrics) → {task_completion, efficiency, tool_usage, error_rate}
  └── evaluate_answer_quality(question, answer, expected) → {accuracy, completeness, ...}
        // 使用 LLM 对回答质量进行 1-10 评分

当前状态: evaluation/ 目录下所有文件为空，尚未实现
```

### 4.11 LLM服务设计

**LLMService：** (详见 `backend/services/llm_service.py`)

```
LLMService(config_path, tool_registry)
  ├── _load_config() → dict         // 读取 ~/.ils4gas/config.json，解析 ${ENV:VAR}
  ├── get_provider(model_id) → LLMProvider  // 创建/缓存 Provider 实例
  ├── get_openai_tools() → [dict]   // 返回 ToolRegistry 中所有工具的 OpenAI schema
  ├── switch_model(model_id)         // 切换当前模型
  ├── list_models() → [{id, name, provider, limit}]
  ├── get_current_model() → dict
  ├── invoke / stream_invoke / ainvoke / astream_invoke(messages)  // 委托到 Provider
  └── tool_registry: ToolRegistry    // 共享的工具注册表
```

---

