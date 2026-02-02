import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Message as MessageType } from '../types';

interface Props extends MessageType {
  isThinking?: boolean;
}

function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 px-2 py-1 rounded bg-[#334155] text-[#94a3b8] hover:bg-[#475569] hover:text-[#e2e8f0] text-xs opacity-0 group-hover:opacity-100 transition-all duration-200"
      title="Copy code"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

export default function Message({ role, content, files, thinking, isThinking }: Props) {
  const isUser = role === 'human';
  // Normalize content: multimodal format (array of blocks) → plain string
  const normalizedContent = Array.isArray(content)
    ? (content as Array<{ type?: string; text?: string }>)
        .filter((b) => b.type === 'text')
        .map((b) => b.text ?? '')
        .join(' ')
    : content;
  const [showThinking, setShowThinking] = useState(false);
  const thinkingRef = useRef<HTMLDivElement>(null);
  const thinkingUserScrolledUp = useRef(false);
  const thinkingLastScrollTop = useRef(0);

  const handleThinkingScroll = () => {
    const el = thinkingRef.current;
    if (!el) return;
    const currentTop = el.scrollTop;
    const distanceFromBottom = el.scrollHeight - currentTop - el.clientHeight;

    if (currentTop < thinkingLastScrollTop.current && distanceFromBottom > 20) {
      thinkingUserScrolledUp.current = true;
    }
    if (distanceFromBottom < 10) {
      thinkingUserScrolledUp.current = false;
    }
    thinkingLastScrollTop.current = currentTop;
  };

  useEffect(() => {
    const el = thinkingRef.current;
    if (!isThinking || !el || thinkingUserScrolledUp.current) return;
    el.scrollTop = el.scrollHeight;
  }, [thinking, isThinking]);

  const thinkingDone = !isThinking && !!thinking;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3 animate-messageIn`}>
      <div
        className={`rounded-2xl px-5 py-3 leading-relaxed ${
          isUser
            ? 'max-w-[80%] bg-gradient-to-br from-[#7c3aed] to-[#533483] text-white'
            : 'max-w-[750px] bg-[#1e293b] text-[#e2e8f0] border border-[#334155] shadow-sm'
        }`}
      >
        {isUser && files && files.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-block bg-[#7c3aed] text-white text-xs px-2 py-0.5 rounded-full"
              >
                {f.name}
              </span>
            ))}
          </div>
        )}

        {/* Live streaming: show thinking text as it arrives */}
        {!isUser && isThinking && thinking && (
          <div className="mb-2">
            <p className="text-xs text-[#06b6d4] font-medium mb-1 flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-[#06b6d4] animate-pulse" />
              Thinking...
            </p>
            <div ref={thinkingRef} onScroll={handleThinkingScroll} className="pl-3 border-l-2 border-[#06b6d4]/40 text-sm text-[#94a3b8] italic whitespace-pre-wrap max-h-40 overflow-y-auto">
              {thinking}
            </div>
          </div>
        )}

        {/* Still waiting for first thinking token */}
        {!isUser && isThinking && !thinking && (
          <p className="text-sm text-[#06b6d4] italic animate-pulse">Thinking...</p>
        )}

        {/* Thinking done: collapsible summary */}
        {!isUser && thinkingDone && (
          <div className="mb-2">
            <button
              onClick={() => setShowThinking((v) => !v)}
              className="text-xs text-[#94a3b8] hover:text-[#e2e8f0] flex items-center gap-1 transition-colors"
            >
              <span
                className="inline-block transition-transform duration-200"
                style={{ transform: showThinking ? 'rotate(90deg)' : 'rotate(0deg)' }}
              >
                &#9654;
              </span>
              Thought for a moment
            </button>
            {showThinking && (
              <div className="mt-1 pl-3 border-l-2 border-[#334155] text-sm text-[#94a3b8] italic whitespace-pre-wrap max-h-60 overflow-y-auto">
                {thinking}
              </div>
            )}
          </div>
        )}

        {isUser ? (
          normalizedContent ? <p className="whitespace-pre-wrap">{normalizedContent}</p> : null
        ) : (
          <div className="prose prose-sm prose-invert max-w-none prose-p:text-[#e2e8f0] prose-headings:text-[#e2e8f0] prose-strong:text-[#e2e8f0] prose-code:text-[#06b6d4] prose-code:bg-[#0f172a] prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-[#0f172a] prose-pre:border prose-pre:border-[#334155] prose-a:text-[#7c3aed] prose-a:no-underline hover:prose-a:underline">
            <ReactMarkdown
              components={{
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {children}
                  </a>
                ),
                pre: ({ children }) => {
                  const codeElement = children as React.ReactElement<{ children: string }>;
                  const code = codeElement?.props?.children || '';
                  return (
                    <div className="relative group">
                      <CopyButton code={code} />
                      <pre className="!bg-[#0f172a] !border-[#334155] !p-4 !mt-0">{children}</pre>
                    </div>
                  );
                },
              }}
            >{normalizedContent}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
