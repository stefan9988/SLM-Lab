import { useState, useRef, type KeyboardEvent, type ChangeEvent } from 'react';
import type { FileAttachment } from '../types';

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

export default function MessageInput({ onSend, disabled, streaming, onStop }: Props) {
  const [text, setText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const selected = Array.from(e.target.files);
    setError(null);

    for (const f of selected) {
      if (f.size > MAX_FILE_SIZE) {
        setError(`File "${f.name}" exceeds 10MB limit.`);
        e.target.value = '';
        return;
      }
    }

    const totalSize = [...files, ...selected].reduce((s, f) => s + f.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
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
      reader.onerror = reject;
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
  };

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t p-3">
      {error && (
        <p className="text-red-500 text-xs mb-2">{error}</p>
      )}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {files.map((f, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 bg-gray-200 text-gray-700 text-xs px-2 py-1 rounded-full"
            >
              {f.name}
              <button
                type="button"
                className="hover:text-red-500"
                onClick={() => removeFile(i)}
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
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
          className="rounded-lg border border-gray-300 px-3 py-2 text-gray-500 hover:text-gray-700 hover:border-gray-400 disabled:opacity-50"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          title="Attach files"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
          </svg>
        </button>
        <textarea
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          rows={1}
          placeholder="Type a message…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
        />
        {streaming ? (
          <button
            className="rounded-lg bg-red-600 px-4 py-2 text-white text-sm font-medium hover:bg-red-700"
            onClick={onStop}
            type="button"
          >
            Stop
          </button>
        ) : (
          <button
            className="rounded-lg bg-blue-600 px-4 py-2 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            onClick={handleSend}
            disabled={disabled || (!text.trim() && files.length === 0)}
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
}
