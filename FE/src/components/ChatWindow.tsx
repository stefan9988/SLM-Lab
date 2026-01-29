import { useEffect, useRef } from 'react';
import type { Message as MessageType } from '../types';
import Message from './Message';
import ToolNotification from './ToolNotification';

interface Props {
  messages: MessageType[];
  toolStatus: string | null;
}

export default function ChatWindow({ messages, toolStatus }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, toolStatus]);

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.length === 0 && (
        <p className="text-center text-gray-400 mt-20">Send a message to start chatting.</p>
      )}
      {messages.map((msg, i) => (
        <Message key={i} {...msg} />
      ))}
      {toolStatus && <ToolNotification status={toolStatus} />}
      <div ref={bottomRef} />
    </div>
  );
}
