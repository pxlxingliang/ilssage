# MCP工具集成方案（增强版）

本文档详细描述 MCP工具集成方案（增强版），对应主文档第 4.4 部分。

### 4.4 MCP工具集成方案（增强版）

MCP (Model Context Protocol) 是本框架的核心工具集成协议。支持三种传输方式，多服务器管理，以及工具懒加载。

**MCP服务器配置结构：** (详见 `~/.ilssage/config.json` 的 `mcp_servers` 字段，解析逻辑见 `backend/tools/mcp_adapter.py` 的 `MCPServerConfig`)

```
mcp_servers: [
  {
    name, description, transport,     // 名称、描述、传输协议(stdio|sse|http)
    command, args, env,               // stdio 模式: 启动命令 + 环境变量
    url,                               // sse/http 模式: 服务地址
    auto_connect,                      // 是否自动连接
    tool_allowlist, tool_denylist,     // 工具白名单/黑名单
    timeout_ms                         // 超时
  }
]
```

**MCP传输层抽象：** (详见 `backend/tools/mcp_adapter.py`)

```
MCPTransport (ABC)
  ├── connect() / disconnect()        // 连接/断开
  ├── list_tools() → [schema]         // 发现工具
  ├── call_tool(name, args) → result  // 调用工具
  └── list_resources() / read_resource(uri)

StdioTransport    — 子进程 stdio 通信，JSON-RPC 协议
SSETransport      — HTTP Server-Sent Events，端点发现
HTTPTransport     — RESTful POST 调用
```

**MCP服务器管理器：** (详见 `backend/tools/mcp_manager.py`)

```
MCPServerManager
  ├── connect_server(config)           // 根据 transport 创建适配器、连接、发现工具
  ├── get_tool(name) → ToolAdapter    // 命名空间隔离: server_name__tool_name
  ├── list_all_tools() → [{name, server, description}]
  └── disconnect_all()
```
