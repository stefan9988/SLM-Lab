import type { Message, SSEEvent, FileAttachment } from '../types';

export async function fetchHistory(sessionId: string): Promise<Message[]> {
  const res = await fetch(`/history?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error('Failed to fetch history');
  const data = await res.json();
  return data.history;
}

export async function clearHistory(sessionId: string): Promise<void> {
  const res = await fetch(`/history?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to clear history');
}

export async function* streamChat(
  message: string,
  sessionId: string,
  files?: FileAttachment[],
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent | 'DONE'> {
  const res = await fetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, files }),
    signal,
  });

  if (!res.ok) throw new Error('Stream request failed');

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop()!;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data: ')) continue;
      const payload = trimmed.slice(6);
      if (payload === '[DONE]') {
        yield 'DONE';
        return;
      }
      try {
        yield JSON.parse(payload) as SSEEvent;
      } catch {
        // skip malformed events
      }
    }
  }
}
