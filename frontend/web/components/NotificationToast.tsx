import React, { useState, useCallback, useEffect, useRef } from 'react';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  action?: { label: string; onClick: () => void };
}

interface NotificationToastProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

const TOAST_ICONS: Record<Toast['type'], { icon: string; color: string; bg: string }> = {
  success: { icon: 'fa-check-circle', color: '#22c55e', bg: 'rgba(34, 197, 94, 0.1)' },
  error: { icon: 'fa-circle-exclamation', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' },
  warning: { icon: 'fa-triangle-exclamation', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
  info: { icon: 'fa-circle-info', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
};

const ToastItem: React.FC<{ toast: Toast; onDismiss: (id: string) => void }> = ({ toast, onDismiss }) => {
  const config = TOAST_ICONS[toast.type];
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    const duration = toast.duration ?? 4000;
    timerRef.current = setTimeout(() => onDismiss(toast.id), duration);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [toast.id, toast.duration, onDismiss]);

  return (
    <div
      className="flex items-start gap-3 px-4 py-3 bg-[#161616] border border-[#2a2a2a] rounded-xl shadow-xl max-w-sm"
      style={{ animation: 'slide-in-right 0.3s ease-out' }}
    >
      <div className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0 mt-0.5" style={{ background: config.bg }}>
        <i className={`fa-solid ${config.icon} text-[11px]`} style={{ color: config.color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-semibold text-[#ddd]">{toast.title}</div>
        {toast.message && (
          <div className="text-[10px] text-[#777] mt-0.5">{toast.message}</div>
        )}
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="mt-1.5 text-[10px] font-semibold text-orange-500 hover:text-orange-400 transition-colors"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-[10px] text-[#444] hover:text-[#888] transition-colors flex-shrink-0 mt-0.5"
      >
        <i className="fa-solid fa-xmark" />
      </button>
    </div>
  );
};

const NotificationToast: React.FC<NotificationToastProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-12 right-4 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
};

export default NotificationToast;
