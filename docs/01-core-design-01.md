# 上下文工程（Workspace 配置层）

本文档详细描述 上下文工程（Workspace 配置层），对应主文档第 4.1 部分。

### 4.1 上下文工程（Workspace 配置层）

参考 hello-agents 上下文工程理念，Agent 在启动时会从工作区加载多层配置，构建完整的上下文理解。

**工作区文件结构（用户目录）：**
```
~/.ilssage/workspace/
├── AGENT.md        # Agent 全局行为配置（工具使用策略、回复风格、安全规则）
├── PERSONA.md      # Agent 人设定义（角色、语气、专业领域）
├── MEMORY.md       # 长期记忆文件（用户偏好、历史决策、关键信息）
├── TOOLS.md        # 工具使用说明（可选，覆盖默认工具描述）
└── SKILLS.md       # Skill 使用指南（可选）
```

**上下文加载流程：** (详见 `backend/core/context.py`)

```
WorkspaceContext(workspace_path)
  ├── _files: 映射到 AGENT.md / PERSONA.md / MEMORY.md / TOOLS.md / SKILLS.md
  │
  ├── load_context() → {key: content}   // 读取所有存在的文件
  ├── build_system_prompt() → str       // 合并 persona + agent + memory + tools 为系统提示词
  ├── update_memory(content)            // 追加行到 MEMORY.md
  └── write_file(name, content)         // 写入指定的上下文文件
```

**上下文加载时机：**
- Agent 初始化时加载一次作为 system prompt
- 用户可通过对话指令动态修改（如 "请记住我喜欢简洁的回答" → 写入 MEMORY.md）
- 支持多用户隔离（每个用户有独立的 workspace 子目录）