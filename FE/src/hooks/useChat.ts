import { useState, useCallback, useRef } from 'react';
import type { Message, FileAttachment } from '../types';
import { streamChat, fetchHistory } from '../utils/api';
import logger from '../utils/logger';

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const [thinkingActive, setThinkingActive] = useState(false);
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
    setThinkingActive(false);
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
      setThinkingActive(false);

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
            setThinkingActive(false);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
          } else if (event.type === 'thinking') {
            logger.debug('[useChat] Received thinking block');
            aiMsg.thinking = (aiMsg.thinking || '') + event.content;
            setToolStatus(null);
            setThinkingActive(true);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
          } else if (event.type === 'tool_use') {
            const toolInfo = JSON.parse(event.content);
            aiMsg.tools_used = [...(aiMsg.tools_used || []), toolInfo];
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
          } else if (event.type === 'status') {
            logger.debug('[useChat] Tool status:', event.content);
            setToolStatus(event.content);
            setThinkingActive(false);
          } else if (event.type === 'error') {
            logger.error('[useChat] LLM error received:', event.content);
            aiMsg.content = `*[${event.content}]*`;
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...aiMsg };
              return next;
            });
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
        setThinkingActive(false);
      }
    },
    [sessionId, streaming],
  );

  return { messages, streaming, toolStatus, thinkingActive, sendMessage, loadHistory, stopStreaming };
}
