import { useCallback, useEffect, useRef } from 'react';
import type { Message as MessageType } from '../types';
import Message from './Message';
import ToolNotification from './ToolNotification';

interface Props {
  messages: MessageType[];
  toolStatus: string | null;
  streaming?: boolean;
}

export default function ChatWindow({ messages, toolStatus, streaming }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);
  const lastScrollTop = useRef(0);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const currentTop = el.scrollTop;
    const distanceFromBottom = el.scrollHeight - currentTop - el.clientHeight;

    // User scrolled up → disengage
    if (currentTop < lastScrollTop.current && distanceFromBottom > 50) {
      userScrolledUp.current = true;
    }

    // User reached bottom → re-engage
    if (distanceFromBottom < 20) {
      userScrolledUp.current = false;
    }

    lastScrollTop.current = currentTop;
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || userScrolledUp.current) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, toolStatus]);

  return (
    <div ref={containerRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-4">
      {messages.length === 0 && (
        <p className="text-center text-gray-400 mt-20">Send a message to start chatting.</p>
      )}
      {messages.map((msg, i) => {
        const isLastAi = msg.role === 'ai' && i === messages.length - 1;
        const isThinking = isLastAi && streaming && msg.thinking && !msg.content;
        return <Message key={i} {...msg} isThinking={!!isThinking} />;
      })}
      {toolStatus && <ToolNotification status={toolStatus} />}
    </div>
  );
}
