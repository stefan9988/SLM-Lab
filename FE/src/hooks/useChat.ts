import { useState, useCallback, useRef } from 'react';
import type { Message, FileAttachment } from '../types';
import { streamChat, fetchHistory, clearHistory } from '../utils/api';
import logger from '../utils/logger';

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(async () => {
    logger.info('[useChat] Loading history for session:', sessionId);
    try {
      const history = await fetchHistory(sessionId);
      logger.info('[useChat] History loaded:', history.length, 'messages');
      setMessages(history.map((m: Message) => ({ ...m, id: m.id || crypto.randomUUID() })));
    } catch (err) {
      logger.error('[useChat] Failed to load history:', err);
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

      logger.info('[useChat] Sending message:', text.slice(0, 50), text.length > 50 ? '...' : '', 'with', files?.length || 0, 'files');
      const controller = new AbortController();
      abortRef.current = controller;

      const userMsg: Message = { id: crypto.randomUUID(), role: 'human', content: text, files };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming(true);
      setToolStatus(null);

      const aiMsg: Message = { id: crypto.randomUUID(), role: 'ai', content: '' };
      setMessages((prev) => [...prev, { ...aiMsg }]);

      try {
        for await (const event of streamChat(text, sessionId, files, controller.signal)) {
          if (event === 'DONE') {
            logger.info('[useChat] Stream complete');
            break;
          }
          if (event.type === 'token') {
            aiMsg.content += event.content;
            setToolStatus(null);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
          } else if (event.type === 'thinking') {
            logger.debug('[useChat] Received thinking block');
            aiMsg.thinking = (aiMsg.thinking || '') + event.content;
            setToolStatus(null);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
          } else if (event.type === 'status') {
            logger.debug('[useChat] Tool status:', event.content);
            setToolStatus(event.content);
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          // Stream aborted intentionally
        } else {
          logger.error('[useChat] Stream error:', err);
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
    } catch (err) {
      logger.error('[useChat] Failed to clear history:', err);
    }
    setMessages([]);
  }, [sessionId]);

  return { messages, streaming, toolStatus, sendMessage, loadHistory, clearChat, stopStreaming };
}
