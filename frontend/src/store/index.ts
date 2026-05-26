import { useState, useCallback } from "react";

let globalState: {
  sessions: any[];
  currentSessionId: string;
  models: any[];
  currentModelId: string;
  theme: "light" | "dark";
} = {
  sessions: [],
  currentSessionId: "",
  models: [],
  currentModelId: "",
  theme: (localStorage.getItem("ilssage_theme") as "light" | "dark") || "light",
};

const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((fn) => fn());
}

export function useStore() {
  const [, setTick] = useState(0);

  useState(() => {
    listeners.add(() => setTick((t) => t + 1));
  });

  return {
    sessions: globalState.sessions,
    currentSessionId: globalState.currentSessionId,
    models: globalState.models,
    currentModelId: globalState.currentModelId,
    theme: globalState.theme,

    setSessions: useCallback((sessions: any[]) => {
      globalState.sessions = sessions;
      notify();
    }, []),
    setCurrentSessionId: useCallback((id: string) => {
      globalState.currentSessionId = id;
      notify();
    }, []),
    setModels: useCallback((models: any[]) => {
      globalState.models = models;
      notify();
    }, []),
    setCurrentModelId: useCallback((id: string) => {
      globalState.currentModelId = id;
      notify();
    }, []),
    toggleTheme: useCallback(() => {
      globalState.theme = globalState.theme === "light" ? "dark" : "light";
      localStorage.setItem("ilssage_theme", globalState.theme);
      document.documentElement.setAttribute("data-theme", globalState.theme);
      notify();
    }, []),
  };
}

export function initTheme() {
  const theme =
    (localStorage.getItem("ilssage_theme") as "light" | "dark") || "light";
  document.documentElement.setAttribute("data-theme", theme);
}
