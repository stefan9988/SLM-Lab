import { useState, useCallback, useRef } from 'react';
import type { Message, FileAttachment } from '../types';
import { streamChat, fetchHistory, clearHistory } from '../utils/api';

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const history = await fetchHistory(sessionId);
      setMessages(history);
    } catch {
      setMessages([]);
    }
  }, [sessionId]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setToolStatus(null);
  }, []);

  const sendMessage = useCallback(
    async (text: string, files?: FileAttachment[]) => {
      if (streaming) return;

      const controller = new AbortController();
      abortRef.current = controller;

      const userMsg: Message = { role: 'human', content: text, files };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming(true);
      setToolStatus(null);

      const aiMsg: Message = { role: 'ai', content: '' };
      setMessages((prev) => [...prev, aiMsg]);

      try {
        for await (const event of streamChat(text, sessionId, files, controller.signal)) {
          if (event === 'DONE') break;
          if (event.type === 'token') {
            aiMsg.content += event.content;
            setToolStatus(null);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
          } else if (event.type === 'thinking') {
            aiMsg.thinking = (aiMsg.thinking || '') + event.content;
            setToolStatus(null);
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
        if (err instanceof DOMException && err.name === 'AbortError') {
          // Intentional abort — not an error
        } else {
          aiMsg.content += '\n\n*[Error: connection lost]*';
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...aiMsg };
            return next;
          });
        }
      } finally {
        abortRef.current = null;
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

  return { messages, streaming, toolStatus, sendMessage, loadHistory, clearChat, stopStreaming };
}
