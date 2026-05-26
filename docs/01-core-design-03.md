# 会话管理设计（SQLite持久化）

本文档详细描述 会话管理设计（SQLite持久化），对应主文档第 4.3 部分。

### 4.3 会话管理设计（SQLite持久化）

**会话表结构（~/.ilssage/data/sessions.db）：**

```sql
-- 会话表
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '新对话',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',  -- JSON: token_count, mcp_servers_used, total_tool_calls
    is_active INTEGER DEFAULT 1
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- user / assistant / system / tool
    content TEXT NOT NULL,
    tool_calls TEXT,     -- JSON array: [{tool_name, args, result}]
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_messages_session ON messages(session_id, timestamp);
CREATE INDEX idx_sessions_updated ON sessions(updated_at DESC);
```

**会话服务设计：** (详见 `backend/services/session_service.py`)

```
SessionService(db_path)
  ├── _init_db() → 创建 sessions + messages 表及索引
  ├── create_session(provider, model, title) → session_id
  ├── list_sessions(limit) → [{id, title, ...}]
  ├── add_message(session_id, role, content, tool_calls) → msg_id
  ├── get_messages(session_id, limit) → [{role, content, tool_calls, ...}]
  └── switch_model(session_id, provider, model) → 更新会话的模型配置
```
