import { useEffect, useState, useRef } from "react";
import { useLocale } from "../../hooks/useLocale";
import { useStore } from "../../store";

interface ContextMenuState {
  sessionId: string;
  x: number;
  y: number;
}

export function SessionList() {
  const { t } = useLocale();
  const {
    sessions,
    currentSessionId,
    setCurrentSessionId,
    setSessions,
  } = useStore();

  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        setContextMenu(null);
      }
    };
    if (contextMenu) {
      document.addEventListener("click", handleClickOutside);
    }
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, [contextMenu]);

  useEffect(() => {
    if (editingSessionId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingSessionId]);

  const createSession = async () => {
    try {
      const res = await fetch("/api/v1/sessions", { method: "POST" });
      const data = await res.json();
      const updated = await fetch("/api/v1/sessions").then((r) => r.json());
      setSessions(updated.sessions || []);
      setCurrentSessionId(data.id);
    } catch (e) {
      console.error(e);
    }
  };

  const deleteSession = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    await fetch(`/api/v1/sessions/${id}`, { method: "DELETE" });
    const updated = await fetch("/api/v1/sessions").then((r) => r.json());
    setSessions(updated.sessions || []);
    if (currentSessionId === id) {
      setCurrentSessionId(updated.sessions?.[0]?.id || "");
    }
  };

  const handleContextMenu = (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({ sessionId, x: e.clientX, y: e.clientY });
  };

  const handleDeleteFromMenu = () => {
    if (!contextMenu) return;
    deleteSession(contextMenu.sessionId);
    setContextMenu(null);
  };

  const handleGenerateTitle = async () => {
    if (!contextMenu) return;
    try {
      await fetch(`/api/v1/sessions/${contextMenu.sessionId}/generate-title`, {
        method: "POST",
      });
      const updated = await fetch("/api/v1/sessions").then((r) => r.json());
      setSessions(updated.sessions || []);
    } catch (e) {
      console.error(e);
    }
    setContextMenu(null);
  };

  const handleSetTitle = () => {
    if (!contextMenu) return;
    const session = sessions.find((s: any) => s.id === contextMenu.sessionId);
    if (session) {
      setEditTitle(session.title || "");
      setEditingSessionId(contextMenu.sessionId);
    }
    setContextMenu(null);
  };

  const handleSaveTitle = async (id: string) => {
    const trimmed = editTitle.trim();
    if (trimmed) {
      await fetch(`/api/v1/sessions/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: trimmed }),
      });
      const updated = await fetch("/api/v1/sessions").then((r) => r.json());
      setSessions(updated.sessions || []);
    }
    setEditingSessionId(null);
    setEditTitle("");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--border-color)",
        }}
      >
        <button
          onClick={createSession}
          style={{
            width: "100%",
            padding: "8px 0",
            borderRadius: "6px",
            background: "var(--accent)",
            color: "white",
            fontSize: "14px",
            fontWeight: 500,
          }}
        >
          + {t.sidebar.newChat}
        </button>
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: "8px" }}>
        {sessions.length === 0 && (
          <div
            style={{
              padding: "16px",
              color: "var(--text-muted)",
              fontSize: "13px",
              textAlign: "center",
            }}
          >
            {t.sidebar.noSessions}
          </div>
        )}
        {sessions.map((s: any) => (
          <div
            key={s.id}
            onClick={() => setCurrentSessionId(s.id)}
            onContextMenu={(e) => handleContextMenu(s.id, e)}
            style={{
              padding: "10px 12px",
              marginBottom: "2px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "13px",
              background:
                s.id === currentSessionId
                  ? "var(--bg-hover)"
                  : "transparent",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            {editingSessionId === s.id ? (
              <input
                ref={editInputRef}
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveTitle(s.id);
                  if (e.key === "Escape") {
                    setEditingSessionId(null);
                    setEditTitle("");
                  }
                }}
                onBlur={() => handleSaveTitle(s.id)}
                onClick={(e) => e.stopPropagation()}
                style={{
                  flex: 1,
                  padding: "2px 4px",
                  fontSize: "13px",
                  borderRadius: "4px",
                  border: "1px solid var(--accent)",
                  background: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  outline: "none",
                }}
              />
            ) : (
              <span
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flex: 1,
                }}
              >
                {s.title}
              </span>
            )}
            <button
              onClick={(e) => deleteSession(s.id, e)}
              style={{
                marginLeft: "4px",
                padding: "2px 6px",
                fontSize: "11px",
                borderRadius: "4px",
                color: "var(--text-muted)",
                opacity: 0,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = "0")}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      {contextMenu && (
        <div
          ref={contextMenuRef}
          style={{
            position: "fixed",
            left: contextMenu.x,
            top: contextMenu.y,
            zIndex: 1000,
            background: "var(--bg-primary)",
            border: "1px solid var(--border-color)",
            borderRadius: "6px",
            padding: "4px 0",
            minWidth: "140px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          }}
        >
          <button
            onClick={handleDeleteFromMenu}
            style={{
              display: "block",
              width: "100%",
              padding: "6px 12px",
              fontSize: "13px",
              textAlign: "left",
              background: "none",
              border: "none",
              color: "var(--text-primary)",
              cursor: "pointer",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "var(--bg-hover)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "none")
            }
          >
            {t.sidebar.deleteConversation}
          </button>
          <button
            onClick={handleGenerateTitle}
            style={{
              display: "block",
              width: "100%",
              padding: "6px 12px",
              fontSize: "13px",
              textAlign: "left",
              background: "none",
              border: "none",
              color: "var(--text-primary)",
              cursor: "pointer",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "var(--bg-hover)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "none")
            }
          >
            {t.sidebar.generateTitle}
          </button>
          <button
            onClick={handleSetTitle}
            style={{
              display: "block",
              width: "100%",
              padding: "6px 12px",
              fontSize: "13px",
              textAlign: "left",
              background: "none",
              border: "none",
              color: "var(--text-primary)",
              cursor: "pointer",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "var(--bg-hover)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "none")
            }
          >
            {t.sidebar.setTitle}
          </button>
        </div>
      )}
    </div>
  );
}
