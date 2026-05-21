import { useRef, useEffect, useCallback } from "react";

type MessageHandler = (data: any) => void;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}/api/v1/ws/chat`;
    const ws = new WebSocket(url);

    ws.onopen = () => {};

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const handlers = handlersRef.current.get(data.type);
        if (handlers) {
          handlers.forEach((fn) => fn(data));
        }
      } catch {}
    };

    ws.onclose = () => {
      wsRef.current = null;
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, 2000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const on = useCallback((type: string, handler: MessageHandler) => {
    const map = handlersRef.current;
    if (!map.has(type)) map.set(type, new Set());
    map.get(type)!.add(handler);
    return () => {
      map.get(type)?.delete(handler);
    };
  }, []);

  return { send, on };
}
