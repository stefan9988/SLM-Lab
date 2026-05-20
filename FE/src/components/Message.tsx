import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message as MessageType } from '../types';
import logger from '../utils/logger';

interface Props extends MessageType {
  isThinking?: boolean;
}

function extractText(node: React.ReactNode): string {
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (node && typeof node === 'object' && 'props' in node) {
    const element = node as React.ReactElement<{ children?: React.ReactNode }>;
    return extractText(element.props.children);
  }
  return '';
}

function CopyMessageButton({ text, position = 'top' }: { text: string; position?: 'top' | 'bottom' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      logger.debug('[Message] Message copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      logger.error('[Message] Failed to copy message');
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`${position === 'top' ? 'absolute top-2 right-2' : 'absolute bottom-2 right-2'} p-1 rounded bg-[#334155]/80 text-[#94a3b8] hover:bg-[#475569] hover:text-[#e2e8f0] text-xs opacity-0 group-hover:opacity-100 transition-all duration-200 z-10`}
      title="Copy message"
    >
      {copied ? (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
          <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
        </svg>
      )}
    </button>
  );
}

function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      logger.debug('[Message] Code copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      logger.error('[Message] Failed to copy code');
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

export default function Message({ role, content, files, thinking, tools_used, isThinking }: Props) {
  const isUser = role === 'human';
  // Normalize content: multimodal format (array of blocks) → plain string
  const normalizedContent = Array.isArray(content)
    ? content
        .filter((b) => b.type === 'text')
        .map((b) => b.text ?? '')
        .join(' ')
    : content;
  const [showThinking, setShowThinking] = useState(false);
  const [showTools, setShowTools] = useState(false);
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
        className={`group relative rounded-2xl px-5 py-3 leading-relaxed ${
          isUser
            ? 'max-w-[80%] bg-[#2d3f56] text-white'
            : 'max-w-[750px] bg-[#1e293b] text-[#e2e8f0] border border-[#334155] shadow-sm'
        }`}
      >
        {normalizedContent.length > 2000 && <CopyMessageButton text={normalizedContent} />}

        {isUser && files && files.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 bg-slate-700/80 text-white text-xs px-2 py-0.5 rounded-full"
                title={f.file_id ? `file_id: ${f.file_id}` : undefined}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                </svg>
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

        {/* Tools used: collapsible summary */}
        {!isUser && tools_used && tools_used.length > 0 && (
          <div className="mb-2">
            <button
              onClick={() => setShowTools((v) => !v)}
              className="text-xs text-[#94a3b8] hover:text-[#e2e8f0] flex items-center gap-1 transition-colors"
            >
              <span
                className="inline-block transition-transform duration-200"
                style={{ transform: showTools ? 'rotate(90deg)' : 'rotate(0deg)' }}
              >
                &#9654;
              </span>
              Used {tools_used.length} tool{tools_used.length !== 1 ? 's' : ''}
            </button>
            {showTools && (
              <div className="mt-1 pl-3 border-l-2 border-[#334155] text-sm text-[#94a3b8] max-h-60 overflow-y-auto">
                {tools_used.map((tool, i) => (
                  <div key={i} className="mb-1.5 last:mb-0">
                    <span className="font-semibold text-[#e2e8f0]">{tool.name}</span>
                    {Object.keys(tool.args).length > 0 && (
                      <div className="pl-3 mt-0.5">
                        {Object.entries(tool.args).map(([key, value]) => (
                          <div key={key} className="text-xs text-[#64748b]">
                            {key}: <span className="text-[#94a3b8]">{typeof value === 'string' ? `"${value}"` : JSON.stringify(value)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {isUser ? (
          normalizedContent ? (
            <div className="prose prose-sm prose-invert max-w-none prose-p:text-[#e2e8f0]">
              <p className="whitespace-pre-wrap">{normalizedContent}</p>
            </div>
          ) : null
        ) : (
          <div className="prose prose-sm prose-invert max-w-none prose-p:text-[#e2e8f0] prose-headings:text-[#e2e8f0] prose-strong:text-[#e2e8f0] prose-code:text-[#06b6d4] prose-code:bg-[#0f172a] prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-[#0f172a] prose-pre:border prose-pre:border-[#334155] prose-a:text-[#7c3aed] prose-a:no-underline hover:prose-a:underline">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
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
                  const code = extractText(children);
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
        <CopyMessageButton text={normalizedContent} position="bottom" />
      </div>
    </div>
  );
}
