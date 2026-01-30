import { useState, useCallback, useRef } from 'react';
import type { Message, FileAttachment } from '../types';
import { streamChat, fetchHistory, clearHistory } from '../utils/api';

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const abortRef = useRef(false);

  const loadHistory = useCallback(async () => {
    try {
      const history = await fetchHistory(sessionId);
      setMessages(history);
    } catch {
      setMessages([]);
    }
  }, [sessionId]);

  const sendMessage = useCallback(
    async (text: string, files?: FileAttachment[]) => {
      if (streaming) return;
      abortRef.current = false;

      const userMsg: Message = { role: 'human', content: text, files };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming(true);
      setToolStatus(null);

      const aiMsg: Message = { role: 'ai', content: '' };
      setMessages((prev) => [...prev, aiMsg]);

      try {
        for await (const event of streamChat(text, sessionId, files)) {
          if (abortRef.current) break;
          if (event === 'DONE') break;
          if (event.type === 'token') {
            aiMsg.content += event.content;
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
          } else if (event.type === 'status') {
            setToolStatus(event.content);
          }
        }
      } catch (err) {
        aiMsg.content += '\n\n*[Error: connection lost]*';
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...aiMsg };
          return next;
        });
      } finally {
        setStreaming(false);
        setToolStatus(null);
      }
    },
    [sessionId, streaming],
  );

  const clearChat = useCallback(async () => {
    try {
      await clearHistory(sessionId);
    } catch {
      // ignore
    }
    setMessages([]);
  }, [sessionId]);

  return { messages, streaming, toolStatus, sendMessage, loadHistory, clearChat };
}
