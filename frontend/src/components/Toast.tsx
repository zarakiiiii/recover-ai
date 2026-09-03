import React, { useEffect } from 'react';
import { AlertTriangleIcon, CheckCircleIcon, CloseIcon } from './Icons';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  title: string;
  message?: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
};

const ToastItem: React.FC<{ toast: ToastMessage; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss,
}) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(toast.id);
    }, 4500);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const iconColor =
    toast.type === 'success' ? '#10B981' : toast.type === 'error' ? '#EF4444' : '#06B6D4';

  return (
    <div className={`toast-item toast-${toast.type}`}>
      <div className="toast-icon">
        {toast.type === 'success' ? (
          <CheckCircleIcon size={20} color={iconColor} />
        ) : (
          <AlertTriangleIcon size={20} color={iconColor} />
        )}
      </div>
      <div className="toast-content">
        <h4 className="toast-title">{toast.title}</h4>
        {toast.message && <p className="toast-message">{toast.message}</p>}
      </div>
      <button className="toast-close" onClick={() => onDismiss(toast.id)}>
        <CloseIcon size={16} />
      </button>
    </div>
  );
};
