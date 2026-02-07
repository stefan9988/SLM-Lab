import { useCallback, useEffect, useRef } from 'react';
import type { Message as MessageType } from '../types';
import Message from './Message';
import ToolNotification from './ToolNotification';

interface Props {
  messages: MessageType[];
  toolStatus: string | null;
  streaming?: boolean;
  thinkingActive?: boolean;
  onSend: (text: string) => void;
}

const suggestions = [
  'Explain how reinforcement learning agents work',
  'Compare DQN and PPO algorithms',
  'Help me configure a new experiment',
];

export default function ChatWindow({ messages, toolStatus, streaming, thinkingActive, onSend }: Props) {
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
    <div ref={containerRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-4 bg-[#0f172a] relative">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full pb-20">
          <h2 className="text-2xl font-bold text-[#e2e8f0] mb-2">SLM Lab</h2>
          <p className="text-[#94a3b8] text-sm mb-8">What can I help you with?</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl w-full px-4">
            {suggestions.map((text) => (
              <div
                key={text}
                onClick={() => onSend(text)}
                className="rounded-xl border border-[#334155] bg-[#1e293b] p-4 text-sm text-[#94a3b8] hover:border-[#7c3aed] transition-colors cursor-pointer"
              >
                {text}
              </div>
            ))}
          </div>
        </div>
      )}
      {messages.map((msg, i) => {
        const isLastAi = msg.role === 'ai' && i === messages.length - 1;
        const isThinking = isLastAi && streaming && thinkingActive && !!msg.thinking;
        return <Message key={msg.id ?? i} {...msg} isThinking={!!isThinking} />;
      })}
      {toolStatus && <ToolNotification status={toolStatus} />}
    </div>
  );
}
