import React from 'react'
import { Check, Info, AlertTriangle, X } from 'lucide-react'
import type { ToastMessage } from '../types.ts'

type ToastProps = {
  toasts: ToastMessage[]
  onDismiss: (id: string) => void
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null

  return (
    <div className="toast-container" aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => {
        const icon = toast.type === 'warning' ? (
          <AlertTriangle size={15} />
        ) : toast.type === 'info' ? (
          <Info size={15} />
        ) : (
          <Check size={15} />
        )

        return (
          <div key={toast.id} className={`toast-card toast-${toast.type ?? 'success'}`}>
            <span className="toast-icon">{icon}</span>
            <div className="toast-content">
              <strong>{toast.title}</strong>
              {toast.detail && <small>{toast.detail}</small>}
            </div>
            <button
              className="toast-dismiss"
              onClick={() => onDismiss(toast.id)}
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}

