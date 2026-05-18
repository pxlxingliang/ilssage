# 4.12 TUI终端界面设计

## 概述

ILS4GAS 提供基于 Textual 的终端用户界面（TUI），支持用户在本地终端直接与智能体交互，无需启动 Web 服务。TUI 与 Web 界面共享完全相同的后端核心，确保两种模式的功能一致性。

## 架构设计

### 目录结构

```
backend/tui/
├── __init__.py           # 模块导出
├── app.py                # TUI 主应用入口
├── screen.py             # 主聊天屏幕
├── chat_handlers.py      # 聊天处理逻辑 Mixin
├── constants.py          # 常量和配置
├── cli.py                # CLI 包装器
└── widgets/              # 自定义组件
    ├── __init__.py
    ├── history.py        # 消息历史组件
    ├── status_bar.py     # 状态栏组件
    ├── command_dropdown.py  # 命令下拉组件
    └── model_select.py   # 模型选择屏幕
```

### 核心组件

#### 1. ILS4GASApp (app.py)
- **职责**：TUI 应用主入口，管理屏幕生命周期
- **功能**：
  - 初始化聊天屏幕
  - 管理全局快捷键（Ctrl+Q 退出）
  - 会话保存和恢复
  - 主题样式管理

#### 2. ChatScreen (screen.py)
- **职责**：主聊天界面，协调各个组件
- **功能**：
  - 组件组合和布局
  - 事件路由
  - 会话初始化和历史加载
  - 输入处理和消息发送

#### 3. ChatHandlerMixin (chat_handlers.py)
- **职责**：聊天业务逻辑的可复用 Mixin
- **功能**：
  - 流式响应处理
  - 命令解析和执行
  - 状态管理（ESC取消、token计数）
  - 模型切换逻辑

#### 4. 组件层 (widgets/)
- **MessageHistory**：消息渲染和历史展示
- **StatusBar**：实时状态和token显示
- **CommandDropdown**：命令自动补全
- **ModelSelectScreen**：模型选择弹窗

## 界面布局

```
┌─────────────────────────────────────────────────────┐
│ ILS4GAS Terminal                                     │ ← Header
├─────────────────────────────────────────────────────┤
│ User: Hello!                                         │
│ ─────────────────────────────────────────────────── │
│ Assistant: Hi there! How can I help you today?      │
│ ─────────────────────────────────────────────────── │
│ [Tool Call: file_read]                               │ ← 可折叠
│ ─────────────────────────────────────────────────── │
│ User: ...                                            │
├─────────────────────────────────────────────────────┤
│ [Type a message... (Enter to send, / for commands)] │ ← Input
│ [/help, /model, /clear, /exit]                      │ ← CommandDropdown
│ thinking...                                          │ ← Thinking indicator
│ model: GPT-4 | tokens: 1,234/128K | ...             │ ← StatusBar
└─────────────────────────────────────────────────────┘
```

## 交互设计

### 1. 消息流

```
用户输入
    ↓
ChatScreen.on_input_submitted()
    ↓
添加到 MessageHistory
    ↓
_session_service.add_message()
    ↓
调用 ChatHandlerMixin._stream_response()
    ↓
Agent.stream_run() → 事件流
    ↓
渲染到界面 + 保存到会话
```

### 2. 命令系统

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助信息 |
| `/model` | 切换 LLM 模型 |
| `/clear` | 开始新会话 |
| `/new` | 同上，别名 |
| `/exit` | 退出应用 |
| `/quit` | 同上，别名 |

### 3. 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+N` | 新建会话 |
| `Esc` | 取消流式输出（快速按两次） |
| `Ctrl+Q` | 退出应用 |
| `Enter` | 发送消息 |

## 消息渲染

### 消息类型处理

TUI 支持多种消息类型的渲染：

1. **用户消息**：普通文本显示
2. **系统消息**：灰色提示样式
3. **助手消息**：流式渲染，支持工具调用
4. **工具调用**：可折叠组件，显示调用参数和结果

### 历史加载逻辑

```python
for msg in messages:
    if msg.role == "tool":
        continue  # 关联到前一个工具调用
    if msg.role == "assistant" and msg.tool_calls:
        # 渲染消息内容
        # 查找关联的 tool 消息并渲染结果
    else:
        # 普通消息渲染
```

## 数据流设计

### 会话历史构建

TUI 使用 `SessionService.build_chat_history()` 与 Web 端共享同一套逻辑：

```
会话消息 → 过滤（移除tool消息、空助手消息） → OpenAI格式 → Agent输入
```

### Token 计数

```python
full_context = system_messages + chat_history
token_count = count_tokens(full_context, model_name)
_status_bar.update(f"tokens: {token_count}/{context_limit}")
```

## 主题系统

### 样式设计

使用 CSS-in-Python 的方式定义主题：

```python
CSS = """
Screen { background: #ffffff; color: #1a1a2e; }
Header { background: #f0f0f5; }
Input:focus { border: solid #6366f1; }
...
"""
```

### 设计原则

- **简洁清晰**：优先内容展示，减少视觉噪音
- **一致性**：与 Web 界面风格保持一致
- **可访问性**：高对比度，支持终端颜色

## 设计模式

### 1. Mixin 模式

使用 `ChatHandlerMixin` 将业务逻辑与界面分离：

```python
class ChatScreen(Screen, ChatHandlerMixin):
    # 界面层代码
    pass

class ChatHandlerMixin:
    # 业务逻辑代码
    async def _stream_response(self, content): ...
    def _handle_command(self, cmd): ...
```

### 2. 组件化设计

所有 UI 元素封装为独立组件：
- 单一职责
- 可复用
- 易于测试

### 3. 事件驱动

使用 Textual 的消息系统实现组件通信：

```python
@on(Input.Changed)
async def handle_input_change(...): ...

@on(ListView.Selected)
async def handle_selection(...): ...
```

## 扩展点

### 1. 自定义命令

在 `constants.py` 中添加新命令：

```python
COMMAND_DESCRIPTIONS = {
    "/mycmd": "Description",
}
```

在 `ChatHandlerMixin._handle_command()` 中实现逻辑。

### 2. 新组件

在 `widgets/` 目录下创建新组件，继承 Textual 的 Widget/Screen。

### 3. 主题自定义

修改 `app.py` 中的 `CSS` 字符串或支持多主题切换。

## 与 Web 界面的一致性

| 特性 | TUI | Web | 共享组件 |
|------|-----|-----|----------|
| 会话管理 | ✓ | ✓ | SessionService |
| 消息历史 | ✓ | ✓ | build_chat_history() |
| 流式输出 | ✓ | ✓ | Agent.stream_run() |
| 工具调用 | ✓ | ✓ | 同一Agent |
| 模型切换 | ✓ | ✓ | LLMService |
| 命令系统 | ✓ | - | TUI特有 |

## 未来规划

- [ ] 会话侧边栏（历史会话列表）
- [ ] 多标签页支持
- [ ] 深色/浅色主题切换
- [ ] 消息搜索和过滤
- [ ] 插件系统支持

---
**文档版本：** v1.0  
**最后更新：** 2026-05-18
