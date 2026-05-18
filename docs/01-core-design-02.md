# LLM配置设计（多Provider抽象）

本文档详细描述 LLM配置设计（多Provider抽象），对应主文档第 4.2 部分。

### 4.2 LLM配置设计（多Provider抽象）

**Provider 抽象层设计：** (详见 `backend/core/llm.py`)

```
LLMProvider (ABC)
  ├── invoke(messages) → str           // 同步调用
  ├── stream_invoke(messages) → stream  // 同步流式调用
  ├── ainvoke(messages) → str          // 异步调用
  ├── astream_invoke(messages) → stream // 异步流式调用
  ├── model_name: str                  // 模型名称
  ├── provider_name: str               // 厂商名称
  └── context_limit: int               // 上下文长度限制

OpenAICompatibleProvider(LLMProvider)
  ├── __init__(api_key, base_url, model_name, context_limit)
  │     // 创建 OpenAI + AsyncOpenAI client
  ├── invoke / stream_invoke          // 通过 OpenAI client 调用
  └── ainvoke / astream_invoke        // 通过 AsyncOpenAI client 调用
```

**~/.ils4gas/config.json 结构：** (详见 `backend/core/config.py` 的 `load_config()`)

```
{
  currentModel: "provider/model_id",     // 当前使用的模型
  providers: {
    "<provider_key>": {
      name, type,                        // 厂商名称、类型(openai-compatible等)
      options: { baseURL, apiKey },      // 连接参数，apiKey 支持 ${ENV:VAR}
      models: {
        "<model_key>": {
          name,                           // 显示名称
          limit: { context, output },     // token 限制
          supports_tools,                 // 是否支持 function calling
          supports_reasoning              // 是否支持推理
        }
      }
    }
  }
}
```

**环境变量解析机制：**
- `${ENV:VOLC_API_KEY}` 表示从环境变量 `VOLC_API_KEY` 读取值
- 在加载配置时自动解析并替换
