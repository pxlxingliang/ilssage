import { useEffect } from "react";
import { useLocale } from "./hooks/useLocale";
import { useStore } from "./store";
import { SessionList } from "./components/SessionList";
import { ModelSelector } from "./components/ModelSelector";
import { ChatPanel } from "./components/ChatPanel";
import { LocaleToggle } from "./components/common/LocaleToggle";

export function App() {
  const { t } = useLocale();
  const {
    sessions,
    currentSessionId,
    setSessions,
    setCurrentSessionId,
    theme,
    toggleTheme,
  } = useStore();

  useEffect(() => {
    fetch("/api/v1/sessions")
      .then((r) => r.json())
      .then((d) => {
        setSessions(d.sessions || []);
      });
  }, []);

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        background: "var(--bg-primary)",
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          width: "var(--sidebar-width)",
          minWidth: "var(--sidebar-width)",
          borderRight: "1px solid var(--border-color)",
          background: "var(--bg-secondary)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            padding: "12px 16px",
            fontSize: "16px",
            fontWeight: 600,
            borderBottom: "1px solid var(--border-color)",
          }}
        >
          {t.app.title}
        </div>
        <div style={{ flex: 1, overflow: "hidden" }}>
          <SessionList />
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Topbar */}
        <div
          style={{
            height: "var(--topbar-height)",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            padding: "0 16px",
            gap: "8px",
          }}
        >
          <ModelSelector />
          <LocaleToggle />
          <button
            onClick={toggleTheme}
            style={{
              padding: "4px 8px",
              fontSize: "12px",
              borderRadius: "4px",
              border: "1px solid var(--border-color)",
              background: "var(--bg-secondary)",
              color: "var(--text-secondary)",
            }}
          >
            {theme === "light" ? "☀" : "☾"}
          </button>
        </div>

        {/* Chat area */}
        <div style={{ flex: 1, overflow: "hidden" }}>
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
