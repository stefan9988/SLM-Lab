import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Message as MessageType } from '../types';

interface Props extends MessageType {
  isThinking?: boolean;
}

export default function Message({ role, content, files, thinking, isThinking }: Props) {
  const isUser = role === 'human';
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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        {isUser && files && files.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-block bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full"
              >
                {f.name}
              </span>
            ))}
          </div>
        )}

        {/* Live streaming: show thinking text as it arrives */}
        {!isUser && isThinking && thinking && (
          <div className="mb-2">
            <p className="text-xs text-gray-400 font-medium mb-1 flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              Thinking...
            </p>
            <div ref={thinkingRef} onScroll={handleThinkingScroll} className="pl-3 border-l-2 border-amber-300 text-sm text-gray-400 italic whitespace-pre-wrap max-h-40 overflow-y-auto">
              {thinking}
            </div>
          </div>
        )}

        {/* Still waiting for first thinking token */}
        {!isUser && isThinking && !thinking && (
          <p className="text-sm text-gray-400 italic animate-pulse">Thinking...</p>
        )}

        {/* Thinking done: collapsible summary */}
        {!isUser && thinkingDone && (
          <div className="mb-2">
            <button
              onClick={() => setShowThinking((v) => !v)}
              className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
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
              <div className="mt-1 pl-3 border-l-2 border-gray-300 text-sm text-gray-400 italic whitespace-pre-wrap max-h-60 overflow-y-auto">
                {thinking}
              </div>
            )}
          </div>
        )}

        {isUser ? (
          content ? <p className="whitespace-pre-wrap">{content}</p> : null
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              components={{
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline hover:text-blue-800"
                  >
                    {children}
                  </a>
                ),
              }}
            >{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
