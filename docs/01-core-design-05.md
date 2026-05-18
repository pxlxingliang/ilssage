# Skills 系统设计

本文档详细描述 Skills 系统设计，对应主文档第 4.5 部分。

### 4.5 Skills 系统设计

Skills 是框架的核心扩展机制，每个 Skill 是一个包含元信息和指令文档的自包含目录。Skill 被实现为一个内置工具（`load_skill`），与 read/write/bash 等工具处于同一层级。

**核心设计理念：按需加载** — Agent 启动时只暴露 skill 摘要列表，LLM 需要时通过 `load_skill` 工具调用加载完整内容。

**Skill 目录结构：**

```
~/.ils4gas/skills/
├── code_review/
│   └── SKILL.md          # Skill 元信息(YAML front matter) + 指令文档(markdown body)
├── code_helper/
│   └── SKILL.md
└── material_analysis/
    └── SKILL.md
```

**SKILL.md 格式：**
```markdown
---
name: code_review
description: Review code for bugs, security, and style. Use when the user asks to review or audit code.
---

# Code Review Skill

## Workflow
1. Examine the provided code for issues.
2. Check for: bugs, security vulnerabilities, performance problems.
3. Report findings with severity levels.
```

- YAML front matter 仅含 `name` 和 `description` 两个字段
- body 部分作为 skill 的 `prompt`（LLM 加载时获取的内容）

**数据模型：** (详见 `backend/tools/builtin/skill.py`)

```
SkillMeta  (元信息)
  ├── name
  └── description

Skill  (完整定义)
  ├── meta: SkillMeta          — 从 SKILL.md YAML 解析
  ├── prompt: str              — SKILL.md body 正文
  └── directory: Path          — skill 目录的绝对路径
```

**按需加载流程：**

```
Agent 启动
  └─> register_builtin_tools()
        └─> create_skill_tool()
              ├─> SkillRegistry.get_summaries()     # 只解析 YAML 摘要，不加载全文
              └─> 返回 ToolInfo("load_skill")       # 注册到 ToolRegistry

用户提问
  └─> LLM 判断需要某个 skill
        └─> 调用 load_skill(name="code_review")
              └─> SkillRegistry.load(name)     # 解析 SKILL.md
              └─> 返回格式化内容:
                    ## Skill: code_review
                    Directory: /root/.ils4gas/skills/code_review

                    [SKILL.md 全文]

后续轮次
  └─> skill 内容已在会话历史的 tool message 中，LLM 可回溯，无需重载
```

**`load_skill` 工具设计：** (详见 `backend/tools/builtin/skill.py`)

```
ToolInfo(
  name = "load_skill"
  description = "Load a skill module's full instructions. Available skills:
                   - code_review: Review code for bugs, security, and style
                   - code_helper: 协助进行代码编写、审查和优化
                   - material_analysis: 材料科学分析助手..."
  parameters:
    name: string, enum=[所有已发现 skill 的名称列表], required
  
  execute(name):
    1. 调用 SkillRegistry.load(name) → 返回 Skill 对象
    2. 格式化输出:
         ## Skill: {skill.meta.name}
         Directory: {skill.directory}

         {skill.prompt}
    3. 返回格式化字符串给 LLM
)
```

**核心类与职责：**

| 类 | 文件 | 职责 |
|----|------|------|
| `SkillRegistry` | `tools/builtin/skill.py` | 扫描目录、解析 SKILL.md YAML front matter、按名称加载、缓存、去重 |
| `SkillMeta` | `tools/builtin/skill.py` | 元信息数据类 (name, description) |
| `Skill` | `tools/builtin/skill.py` | 完整 Skill 定义 (meta + prompt + directory) |

**集成点：** `load_skill` 与其他内置工具一样，由 `register_builtin_tools()` 统一注册到 `ToolRegistry`：

```
# backend/tools/builtin/__init__.py
def register_builtin_tools(registry):
    ...
    skill_tool = create_skill_tool()
    if skill_tool:
        registry.register(skill_tool)
```

该注册在 TUI 和 Web 模式下均自动执行（`backend/tui/screen.py` 和 `backend/main.py`）。

**关键设计决策：**

1. **Skill 即 Tool** — `load_skill` 是标准 `ToolInfo`，与其他 builtin 工具同层级，无需独立的服务/加载器/执行器层
2. **按需加载 vs 启动全量注入** — LLM 自主决定何时加载，避免 context 膨胀
3. **Tool 机制复用** — 完全复用 ReActAgent tool-calling 循环，不修改 Agent 核心代码
4. **跨轮次持久化** — skill 内容作为 tool message 保留在对话历史中，后续轮次自然可见
5. **目录路径暴露** — 工具返回 `Directory: /path/to/skill/`，LLM 可通过 read 工具读取 skill 目录下的附加文件
6. **同名冲突：后者覆盖 + 日志警告** — 多个 `skills_dirs` 中出现同名 skill 时，最后扫描的目录生效，同时输出 `logger.warning()`
7. **摘要不解析全文** — `get_summaries()` 只读 YAML front matter，`load()` 才触发完整解析
