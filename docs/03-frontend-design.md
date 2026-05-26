# 前端界面设计

本文档详细描述 IlsSage 智能体框架的前端界面设计内容，对应主文档的第 6 部分。

## 6. 前端界面设计

### 6.1 技术选型

| 技术 | 选型 | 说明 |
|------|------|------|
| **框架** | React 18 + TypeScript | 组件化开发，类型安全 |
| **构建** | Vite | 快速HMR，ESM原生支持 |
| **状态管理** | Zustand | 轻量级，无模板代码 |
| **Markdown渲染** | react-markdown + rehype-highlight | 支持代码高亮 |
| **代码高亮** | Shiki | 服务端级别的高亮质量 |
| **CSS方案** | CSS Modules + CSS Variables | 组件隔离 + 主题变量 |
| **HTTP客户端** | fetch + EventSource | 原生API，无额外依赖 |
| **虚拟滚动** | @tanstack/react-virtual | 大量消息高性能渲染 |

### 6.2 组件架构

```
App
├── AppShell (布局容器)
│   ├── Sidebar (侧边栏)
│   │   ├── Logo
│   │   ├── NewChatButton
│   │   ├── SessionList
│   │   │   └── SessionItem (可重命名、删除)
│   │   └── SettingsButton
│   │
│   ├── TopBar (顶部栏)
│   │   ├── ModelSelector (模型下拉切换)
│   │   └── ThemeToggle (亮色/暗色切换)
│   │
│   └── MainPanel (主区域)
│       ├── ChatArea (聊天区域)
│       │   ├── MessageList (虚拟滚动消息列表)
│       │   │   ├── UserMessage (用户消息气泡)
│       │   │   ├── AssistantMessage (AI消息)
│       │   │   │   ├── ThinkingBlock (推理过程，可折叠)
│       │   │   │   ├── MarkdownView (Markdown渲染)
│       │   │   │   └── ToolCallCard (工具调用卡片)
│       │   │   │       ├── ToolCallArgs (参数JSON展开)
│       │   │   │       ├── ToolCallDiff (文件编辑diff视图)
│       │   │   │       └── ToolCallResult (执行结果)
│       │   │   └── SystemMessage (系统通知)
│       │   └── ScrollAnchor (自动滚动锚点)
│       │
│       └── InputArea (输入区)
│           ├── AttachButton (附件上传)
│           ├── TextInput (多行文本输入)
│           ├── SendButton / StopButton (发送/停止)
│           └── TokenCounter (Token计数)
│
├── SkillPanel (Skill管理抽屉，可滑出)
│   ├── SkillList
│   └── SkillEditor
│
└── EvalPanel (评估面板)
    ├── EvalForm
    └── EvalResults
```

### 6.3 流式渲染设计

```typescript
// hooks/useStream.ts
interface StreamState {
  content: string;
  thinking: string;
  toolCalls: ToolCall[];
  isStreaming: boolean;
  isThinking: boolean;
}

function useChatStream(sessionId: string): StreamState & {
  send: (message: string) => void;
  cancel: () => void;
} {
  const ws = useRef<WebSocket | null>(null);
  const [state, setState] = useState<StreamState>(initialState);
  
  const connect = useCallback(() => {
    // 首选 WebSocket
    try {
      ws.current = new WebSocket(`ws://${host}/api/v1/ws/chat?session_id=${sessionId}`);
      ws.current.onmessage = handleMessage;
      ws.current.onerror = () => fallbackToSSE();  // 降级到SSE
    } catch {
      fallbackToSSE();
    }
  }, [sessionId]);
  
  const fallbackToSSE = () => {
    // SSE fallback
    const source = new EventSource(`/api/v1/chat/${sessionId}/stream`);
    source.addEventListener('content', ...);
    source.addEventListener('tool_call_start', ...);
    source.addEventListener('done', ...);
  };
  
  return { ...state, send, cancel };
}
```

### 6.4 主题系统（亮色/暗色）

```css
/* styles/theme.css */
:root {
  /* 亮色主题 */
  --bg-primary: #ffffff;
  --bg-secondary: #f7f7f8;
  --bg-tertiary: #ececf1;
  --text-primary: #1a1a2e;
  --text-secondary: #6b7280;
  --border-color: #e5e7eb;
  --accent: #6366f1;
  --accent-hover: #4f46e5;
  --user-msg-bg: #6366f1;
  --user-msg-text: #ffffff;
  --assistant-msg-bg: #f7f7f8;
  --tool-card-bg: #f0fdf4;
  --tool-card-border: #86efac;
  --code-bg: #1e1e2e;
  --error-text: #ef4444;
}

[data-theme="dark"] {
  /* 暗色主题 */
  --bg-primary: #0f0f23;
  --bg-secondary: #1a1a2e;
  --bg-tertiary: #25253e;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --border-color: #2d2d50;
  --accent: #818cf8;
  --accent-hover: #6366f1;
  --user-msg-bg: #6366f1;
  --user-msg-text: #ffffff;
  --assistant-msg-bg: #1a1a2e;
  --tool-card-bg: #0f2f1a;
  --tool-card-border: #22c55e;
  --code-bg: #0d0d1a;
  --error-text: #f87171;
}
```

### 6.5 工具栏可视化设计

工具调用在前端以可折叠卡片形式展示，针对文件编辑类工具提供 diff 视图：

```typescript
// components/ToolCallCard/ToolCallDiff.tsx
interface DiffViewProps {
  toolName: string;
  args: Record<string, any>;
  result: string;
  isError: boolean;
  durationMs: number;
}

function ToolCallCard({ toolName, args, result, isError, durationMs }: DiffViewProps) {
  const [expanded, setExpanded] = useState(false);
  
  const isFileEdit = ['edit_file', 'write_file', 'multi_edit_file'].includes(toolName);
  
  return (
    <div className={cn(styles.card, isError && styles.cardError)}>
      <div className={styles.header} onClick={() => setExpanded(!expanded)}>
        <span className={styles.icon}>{isFileEdit ? '📝' : '🔧'}</span>
        <span className={styles.name}>{toolName}</span>
        <span className={styles.duration}>{durationMs}ms</span>
        <span className={styles.chevron}>{expanded ? '▾' : '▸'}</span>
      </div>
      
      {expanded && (
        <div className={styles.body}>
          {isFileEdit ? (
            <DiffView oldString={args.old_string} newString={args.new_string} />
          ) : (
            <pre className={styles.args}>{JSON.stringify(args, null, 2)}</pre>
          )}
          <div className={styles.result}>
            {isError ? '❌ ' : '✅ '}{truncate(result, 500)}
          </div>
        </div>
      )}
    </div>
  );
}
```


### 6.6 国际化（i18n）方案

框架采用轻量级 i18n 方案，仅依赖 React Context + JSON 字典，无需引入第三方 i18n 库。

**设计原则：**
- 默认中文、一键切换英文
- 所有文案集中在 locale JSON 文件中，组件内不使用硬编码字符串
- 支持占位符变量插值（如 `{name}`、`{count}`）

**目录结构：**
```
frontend/src/
├── locales/
│   ├── zh-CN.json    # 中文文案（默认）
│   ├── en-US.json    # 英文文案
│   └── index.ts      # 导出类型定义
├── hooks/
│   └── useLocale.ts  # 语言切换 Hook
└── components/
    └── common/
        └── LocaleToggle.tsx  # 语言切换按钮
```

**文案字典（locales/zh-CN.json）：**
```json
{
  "app": { "title": "IlsSage 智能体", "version": "v2.0" },
  "sidebar": {
    "newChat": "新建对话",
    "searchPlaceholder": "搜索会话...",
    "noSessions": "暂无会话"
  },
  "chat": {
    "inputPlaceholder": "输入消息... (Enter 发送, Shift+Enter 换行)",
    "send": "发送",
    "stop": "停止生成",
    "regenerate": "重新生成",
    "copy": "复制",
    "copied": "已复制",
    "thinking": "思考中..."
  },
  "model": {
    "selector": "切换模型",
    "context": "上下文长度",
    "output": "最大输出"
  },
  "tools": {
    "callTitle": "工具调用",
    "executing": "执行中...",
    "result": "结果",
    "duration": "耗时",
    "error": "执行失败"
  },
  "skills": {
    "title": "技能管理",
    "load": "加载技能",
    "unload": "卸载",
    "create": "从对话创建",
    "noSkills": "暂无可用技能"
  },
  "memory": {
    "title": "记忆管理",
    "save": "保存记忆",
    "search": "搜索记忆",
    "empty": "暂无记忆"
  },
  "settings": {
    "title": "设置",
    "theme": "主题",
    "light": "亮色",
    "dark": "暗色",
    "language": "语言",
    "chinese": "中文",
    "english": "English"
  }
}
```

**文案字典（locales/en-US.json）：**
```json
{
  "app": { "title": "IlsSage", "version": "v2.0" },
  "sidebar": {
    "newChat": "New Chat",
    "searchPlaceholder": "Search sessions...",
    "noSessions": "No sessions"
  },
  "chat": {
    "inputPlaceholder": "Type a message... (Enter to send, Shift+Enter for new line)",
    "send": "Send",
    "stop": "Stop",
    "regenerate": "Regenerate",
    "copy": "Copy",
    "copied": "Copied",
    "thinking": "Thinking..."
  },
  "model": {
    "selector": "Switch Model",
    "context": "Context Length",
    "output": "Max Output"
  },
  "tools": {
    "callTitle": "Tool Call",
    "executing": "Executing...",
    "result": "Result",
    "duration": "Duration",
    "error": "Execution Failed"
  },
  "skills": {
    "title": "Skills",
    "load": "Load Skill",
    "unload": "Unload",
    "create": "Create from chat",
    "noSkills": "No skills available"
  },
  "memory": {
    "title": "Memory",
    "save": "Save Memory",
    "search": "Search Memory",
    "empty": "No memories"
  },
  "settings": {
    "title": "Settings",
    "theme": "Theme",
    "light": "Light",
    "dark": "Dark",
    "language": "Language",
    "chinese": "中文",
    "english": "English"
  }
}
```

**类型定义（locales/index.ts）：**
```typescript
export type Locale = 'zh-CN' | 'en-US';

export interface LocaleDict {
  app: { title: string; version: string };
  sidebar: { newChat: string; searchPlaceholder: string; noSessions: string };
  chat: { inputPlaceholder: string; send: string; stop: string; regenerate: string; copy: string; copied: string; thinking: string };
  model: { selector: string; context: string; output: string };
  tools: { callTitle: string; executing: string; result: string; duration: string; error: string };
  skills: { title: string; load: string; unload: string; create: string; noSkills: string };
  memory: { title: string; save: string; search: string; empty: string };
  settings: { title: string; theme: string; light: string; dark: string; language: string; chinese: string; english: string };
}
```

**i18n Context + Hook（hooks/useLocale.ts）：**
```typescript
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { Locale, LocaleDict } from '../locales';
import zhCN from '../locales/zh-CN.json';
import enUS from '../locales/en-US.json';

const localeMap: Record<Locale, LocaleDict> = {
  'zh-CN': zhCN as LocaleDict,
  'en-US': enUS as LocaleDict,
};

interface LocaleContextValue {
  locale: Locale;
  t: LocaleDict;
  setLocale: (l: Locale) => void;
  toggleLocale: () => void;
}

const LocaleContext = createContext<LocaleContextValue>(null!);

const STORAGE_KEY = 'ilssage_locale';

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return (saved as Locale) || 'zh-CN';  // 默认中文
  });

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(STORAGE_KEY, l);
  }, []);

  const toggleLocale = useCallback(() => {
    setLocale(locale === 'zh-CN' ? 'en-US' : 'zh-CN');
  }, [locale, setLocale]);

  const value: LocaleContextValue = {
    locale,
    t: localeMap[locale],
    setLocale,
    toggleLocale,
  };

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}

// 模板插值工具函数
export function interpolate(text: string, vars: Record<string, string | number>): string {
  return text.replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? `{${key}}`));
}
```

**语言切换按钮（components/common/LocaleToggle.tsx）：**
```typescript
import { useLocale } from '../../hooks/useLocale';

export function LocaleToggle() {
  const { locale, toggleLocale } = useLocale();

  return (
    <button
      onClick={toggleLocale}
      className={styles.toggle}
      title={locale === 'zh-CN' ? 'Switch to English' : '切换中文'}
    >
      {locale === 'zh-CN' ? 'EN' : '中'}
    </button>
  );
}
```

**组件使用示例：**
```typescript
// 在任何组件中：
import { useLocale, interpolate } from '../../hooks/useLocale';

function ChatInput() {
  const { t } = useLocale();

  return (
    <div>
      <textarea placeholder={t.chat.inputPlaceholder} />
      <button>{t.chat.send}</button>
    </div>
  );
}

// 带变量的插值：
function ToolCard({ toolName, durationMs }: { toolName: string; durationMs: number }) {
  const { t } = useLocale();
  return (
    <span>{interpolate(t.tools.duration, { name: toolName, ms: durationMs })}</span>
  );
}
```

