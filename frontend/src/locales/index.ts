export type Locale = "zh-CN" | "en-US";

export interface LocaleDict {
  app: { title: string; name: string };
  sidebar: { newChat: string; noSessions: string; delete: string };
  chat: {
    placeholder: string;
    send: string;
    stop: string;
    thinking: string;
    empty: string;
    truncated: string;
    queued: string;
  };
  tokens: {
    input: string;
    prompt: string;
    completion: string;
    total: string;
  };
  model: { selector: string; loading: string; error: string };
  error: { auth: string; network: string; unknown: string };
  settings: {
    title: string;
    theme: string;
    light: string;
    dark: string;
    language: string;
  };
}
