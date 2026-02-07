import { useState, useRef, useEffect, type KeyboardEvent, type ChangeEvent } from 'react';
import type { FileAttachment } from '../types';
import logger from '../utils/logger';

const ACCEPTED_TYPES =
  '.txt,.py,.js,.ts,.json,.csv,.md,.html,.css,.xml,.yaml,.yml,.log,.pdf,.png,.jpg,.jpeg,.gif,.webp';
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_TOTAL_SIZE = 20 * 1024 * 1024;

interface Props {
  onSend: (text: string, files?: FileAttachment[]) => void;
  disabled: boolean;
  streaming: boolean;
  onStop: () => void;
}

const MAX_ROWS = 8;
const MIN_ROWS = 1;
const LINE_HEIGHT = 20;

export default function MessageInput({ onSend, disabled, streaming, onStop }: Props) {
  const [text, setText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const newHeight = Math.min(el.scrollHeight, MAX_ROWS * LINE_HEIGHT);
    el.style.height = `${Math.max(newHeight, MIN_ROWS * LINE_HEIGHT)}px`;
  }, [text]);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleFiles = (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const selected = Array.from(e.target.files);
    setError(null);

    for (const f of selected) {
      if (f.size > MAX_FILE_SIZE) {
        logger.warn('[MessageInput] File too large:', f.name, f.size);
        setError(`File "${f.name}" exceeds 10MB limit.`);
        e.target.value = '';
        return;
      }
    }

    const totalSize = [...files, ...selected].reduce((s, f) => s + f.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
      logger.warn('[MessageInput] Total file size exceeds limit:', totalSize);
      setError('Total file size exceeds 20MB limit.');
      e.target.value = '';
      return;
    }

    setFiles((prev) => [...prev, ...selected]);
    e.target.value = '';
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const readFileAsDataURL = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => {
        logger.error('[MessageInput] Failed to read file:', file.name);
        reject(reader.error);
      };
      reader.readAsDataURL(file);
    });

  const handleSend = async () => {
    const trimmed = text.trim();
    if ((!trimmed && files.length === 0) || disabled) return;

    let attachments: FileAttachment[] | undefined;
    if (files.length > 0) {
      attachments = await Promise.all(
        files.map(async (f) => ({
          name: f.name,
          type: f.type,
          content: await readFileAsDataURL(f),
          size: f.size,
        })),
      );
    }

    onSend(trimmed, attachments);
    setText('');
    setFiles([]);
    setError(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-[#0f172a] px-4 py-3">
      {error && (
        <p className="text-[#ef4444] text-xs mb-2">{error}</p>
      )}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {files.map((f, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 bg-[#0f3460] text-[#e2e8f0] text-xs px-2 py-1 rounded-full border border-[#334155]"
            >
              {f.name}
              <button
                type="button"
                className="hover:text-[#ef4444] transition-colors"
                onClick={() => removeFile(i)}
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2 bg-[#1e293b] border border-[#334155] rounded-xl px-3 py-2 focus-within:ring-2 focus-within:ring-[#7c3aed] focus-within:border-[#7c3aed] transition-all duration-200">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={handleFiles}
        />
        <button
          type="button"
          className="p-1.5 text-[#94a3b8] hover:text-[#e2e8f0] disabled:opacity-50 transition-colors duration-200"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          title="Attach files"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
          </svg>
        </button>
        <textarea
          ref={textareaRef}
          className="flex-1 resize-none bg-transparent text-[#e2e8f0] placeholder-[#94a3b8] py-1 focus:outline-none text-sm overflow-y-auto"
          rows={MIN_ROWS}
          placeholder="Type a message…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
        />
        {streaming ? (
          <button
            className="flex-shrink-0 w-8 h-8 rounded-full bg-[#ef4444] flex items-center justify-center text-white hover:bg-[#dc2626] transition-colors duration-200"
            onClick={onStop}
            type="button"
            title="Stop"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 16 16">
              <rect x="3" y="3" width="10" height="10" rx="1" />
            </svg>
          </button>
        ) : (
          <button
            className="flex-shrink-0 w-8 h-8 rounded-full bg-[#7c3aed] flex items-center justify-center text-white hover:bg-[#6d28d9] disabled:opacity-50 transition-colors duration-200"
            onClick={handleSend}
            disabled={disabled || (!text.trim() && files.length === 0)}
            title="Send"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
