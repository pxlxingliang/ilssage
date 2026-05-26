import React, { createContext, useContext, useState, useCallback } from "react";
import type { Locale, LocaleDict } from "../locales";
import zhCN from "../locales/zh-CN.json";
import enUS from "../locales/en-US.json";

const localeMap: Record<Locale, LocaleDict> = {
  "zh-CN": zhCN as LocaleDict,
  "en-US": enUS as LocaleDict,
};

interface LocaleContextValue {
  locale: Locale;
  t: LocaleDict;
  toggleLocale: () => void;
}

const LocaleContext = createContext<LocaleContextValue>(null!);

const STORAGE_KEY = "ilssage_locale";

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return (saved as Locale) || "zh-CN";
  });

  const toggleLocale = useCallback(() => {
    setLocale((prev) => {
      const next = prev === "zh-CN" ? "en-US" : "zh-CN";
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  return (
    <LocaleContext.Provider value={{ locale, t: localeMap[locale], toggleLocale }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  return useContext(LocaleContext);
}
