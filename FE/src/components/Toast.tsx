import type { ToastItem } from '../contexts/ToastContext';

interface Props {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 5v4M8 11v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export default function Toast({ toast, onDismiss }: Props) {
  const isSuccess = toast.type === 'success';
  const colors = isSuccess
    ? 'text-[#22c55e] bg-[#22c55e]/10 border-[#22c55e]/30'
    : 'text-[#ef4444] bg-[#ef4444]/10 border-[#ef4444]/30';

  return (
    <div
      role="alert"
      className={`pointer-events-auto flex items-center gap-2 px-4 py-3 rounded-lg text-sm border shadow-lg animate-toastIn ${colors}`}
    >
      {isSuccess ? <CheckIcon /> : <ErrorIcon />}
      <span>{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        className="ml-auto pl-3 opacity-50 hover:opacity-100 transition-opacity"
        aria-label="Dismiss notification"
      >
        <XIcon />
      </button>
    </div>
  );
}
