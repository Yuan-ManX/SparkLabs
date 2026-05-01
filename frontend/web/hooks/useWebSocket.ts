import { useEffect, useRef, useCallback } from 'react';
import { useEditorStore } from '../store/editorStore';

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const isMounted = useRef(true);

  const addLog = useEditorStore((s) => s.addLog);
  const setBackendConnected = useEditorStore((s) => s.setBackendConnected);
  const setEngineStatus = useEditorStore((s) => s.setEngineStatus);
  const setFps = useEditorStore((s) => s.setFps);

  const connect = useCallback(() => {
    if (!isMounted.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const ws = new WebSocket(`${protocol}//${host}:8000/ws/connect`);

    ws.onopen = () => {
      reconnectAttempt.current = 0;
      setBackendConnected(true);
      addLog('success', '[WS] Connected to backend');

      ws.send(JSON.stringify({
        type: 'subscribe',
        channels: ['agent', 'engine', 'logs'],
      }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const store = useEditorStore.getState();

        switch (msg.type) {
          case 'connected':
            break;

          case 'agent_event':
            if (msg.event === 'prompt_result') {
              addLog('success', `[AI Agent] ${msg.data?.prompt?.substring(0, 60) || 'Complete'} — done`);
            } else if (msg.event === 'thinking_step') {
              addLog('info', `[Agent] Thinking: ${(msg.data?.thought || '').substring(0, 80)}`);
            } else if (msg.event === 'tool_execution') {
              addLog('info', `[Agent] Tool: ${msg.data?.tool} — ${msg.data?.status}`);
            } else if (msg.event === 'error_recovery') {
              addLog('warn', `[Agent] Recovery: ${msg.data?.action} (attempt ${msg.data?.attempt})`);
            } else if (msg.event === 'prompt_error') {
              addLog('error', `[Agent] Error: ${msg.data?.error}`);
            }
            break;

          case 'engine_status_update':
            setEngineStatus(msg.data || {});
            if (msg.data?.fps) setFps(msg.data.fps);
            break;

          case 'log':
            addLog(msg.level === 'error' ? 'error' : msg.level === 'warn' ? 'warn' : 'info', msg.message);
            break;

          case 'pong':
            break;
        }
      } catch {
        // ignore parse errors on non-critical messages
      }
    };

    ws.onclose = () => {
      if (!isMounted.current) return;
      setBackendConnected(false);
      addLog('warn', '[WS] Disconnected');

      const delay = RECONNECT_DELAYS[Math.min(reconnectAttempt.current, RECONNECT_DELAYS.length - 1)];
      reconnectAttempt.current += 1;
      reconnectTimer.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [addLog, setBackendConnected, setEngineStatus, setFps]);

  useEffect(() => {
    isMounted.current = true;
    connect();
    return () => {
      isMounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const send = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { send };
}
