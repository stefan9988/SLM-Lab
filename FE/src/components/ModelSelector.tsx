import { useState, useRef, useEffect } from 'react';
import { AVAILABLE_MODELS, MODELS_BY_PROVIDER, PROVIDER_LABELS } from '../constants/models';

interface Props {
  currentProvider: string;
  currentModelName: string;
  onModelChange: (provider: string, modelName: string) => void;
  disabled?: boolean;
  error?: boolean;
}

export default function ModelSelector({ currentProvider, currentModelName, onModelChange, disabled, error }: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const currentModel = AVAILABLE_MODELS.find(
    (m) => m.provider === currentProvider && m.modelName === currentModelName,
  );
  const displayName = currentModel
    ? currentModel.displayName
    : error
      ? 'Unavailable'
      : currentModelName || 'Loading…';

  useEffect(() => {
    if (!open) return;

    const handleMouseDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const handleSelect = (provider: string, modelName: string) => {
    onModelChange(provider, modelName);
    setOpen(false);
  };

  const providerOrder = ['anthropic', 'openrouter', 'ollama'];

  return (
    <div ref={containerRef} className="relative mb-2">
      <button
        type="button"
        onClick={() => !disabled && setOpen((prev) => !prev)}
        disabled={disabled}
        className="inline-flex items-center gap-1 text-xs text-[#94a3b8] hover:text-[#e2e8f0] bg-[#1e293b] border border-[#334155] rounded-full px-2.5 py-1 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="text-[#06b6d4]">Model:</span>
        <span>{displayName}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={`h-3 w-3 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute bottom-full mb-1 left-0 z-20 w-56 rounded-xl border border-[#334155] bg-[#1e293b] shadow-xl py-1"
          role="listbox"
        >
          {providerOrder
            .filter((p) => MODELS_BY_PROVIDER[p])
            .map((provider) => (
              <div key={provider}>
                <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#64748b]">
                  {PROVIDER_LABELS[provider] ?? provider}
                </div>
                {MODELS_BY_PROVIDER[provider].map((model) => {
                  const isSelected =
                    model.provider === currentProvider && model.modelName === currentModelName;
                  return (
                    <button
                      key={model.modelName}
                      type="button"
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => handleSelect(model.provider, model.modelName)}
                      className={`w-full text-left px-3 py-1.5 text-xs transition-colors duration-100 ${
                        isSelected
                          ? 'bg-[#7c3aed]/20 text-[#c4b5fd]'
                          : 'text-[#e2e8f0] hover:bg-[#334155]'
                      }`}
                    >
                      {model.displayName}
                    </button>
                  );
                })}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
