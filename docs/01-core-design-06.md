# 记忆与RAG系统设计

本文档详细描述 记忆与RAG系统设计，对应主文档第 4.6 部分。

### 4.6 记忆与RAG系统设计

记忆系统分为三个层次：短期记忆（会话上下文）、长期记忆（持久化存储）、RAG检索增强（向量语义搜索）。

**短期记忆：** (详见 `backend/memory/short_term.py`)

```
ShortTermMemory(max_turns, max_tokens)
  ├── add(role, content, token_estimate)  // 追加消息，自动裁剪超限
  ├── _trim()                             // 超出 token 上限时弹出最早消息
  ├── get_messages() → [dict]             // 获取滑动窗口内消息
  └── clear()                             // 清空
```

**长期记忆：** (详见 `backend/memory/long_term.py`)

```
LongTermMemory(db_path)
  ├── _init_db() → 创建 memories + conversation_summaries 表
  ├── save(user_id, content, category, importance)
  ├── search(user_id, query, limit) → [dict]
  └── save_summary(session_id, user_id, summary)
```

**RAG检索增强：** (详见 `backend/memory/rag.py`)

```
RAGManager(persist_dir)
  ├── get_or_create_collection(name) → ChromaDB collection
  ├── index_messages(session_id, messages, embedding_fn)  // 消息向量化
  ├── search(session_id, query, embedding_fn) → [dict]    // 语义搜索
  └── index_documents(collection_name, documents, embedding_fn)

ConversationSummarizer(llm)
  └── summarize(messages, max_length) → str  // LLM 压缩长对话为摘要
```
