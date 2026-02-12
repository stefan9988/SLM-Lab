import type { Message, SSEEvent, FileAttachment, ExtractionSchema, SchemaField } from '../types';
import logger from './logger';

const TOKEN_KEY = 'slm-auth-token';
const USER_KEY = 'slm-auth-user';

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

function handleUnauthorized(res: Response): void {
  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.reload();
  }
}

export async function fetchHistory(sessionId: string): Promise<Message[]> {
  logger.info('[API] Fetching history for session:', sessionId);
  const res = await fetch(`/history?session_id=${encodeURIComponent(sessionId)}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Failed to fetch history:', res.status, res.statusText);
    throw new Error('Failed to fetch history');
  }
  const data = await res.json();
  logger.info('[API] Fetched history:', data.history.length, 'messages');
  return data.history;
}

export async function clearHistory(sessionId: string): Promise<void> {
  logger.info('[API] Clearing history for session:', sessionId);
  const res = await fetch(`/history?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Failed to clear history:', res.status, res.statusText);
    throw new Error('Failed to clear history');
  }
  logger.info('[API] History cleared successfully');
}

export interface SessionInfo {
  id: string;
  title: string;
  updated_at: string | null;
}

export async function fetchSessions(): Promise<SessionInfo[]> {
  logger.info('[API] Fetching sessions');
  const res = await fetch('/sessions', {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Failed to fetch sessions:', res.status, res.statusText);
    throw new Error('Failed to fetch sessions');
  }
  const data = await res.json();
  logger.info('[API] Fetched sessions:', data.sessions.length);
  return data.sessions;
}

export async function* streamChat(
  message: string,
  sessionId: string,
  files?: FileAttachment[],
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent | 'DONE'> {
  logger.info('[API] Starting stream chat for session:', sessionId, 'with', files?.length || 0, 'files');
  const res = await fetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ message, session_id: sessionId, files }),
    signal,
  });

  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Stream request failed:', res.status, res.statusText);
    throw new Error('Stream request failed');
  }
  logger.info('[API] Stream connection established');

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
        const event = JSON.parse(payload) as SSEEvent;
        logger.debug('[API] Received SSE event:', event.type);
        yield event;
      } catch {
        logger.warn('[API] Skipping malformed SSE event:', payload);
      }
    }
  }
}

export async function fetchSchemas(): Promise<ExtractionSchema[]> {
  logger.info('[API] Fetching schemas');
  const res = await fetch('/schemas', {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Failed to fetch schemas:', res.status, res.statusText);
    throw new Error('Failed to fetch schemas');
  }
  const data = await res.json();
  logger.info('[API] Fetched schemas:', data.schemas.length);
  return data.schemas;
}

export async function createSchema(name: string, fields: SchemaField[]): Promise<ExtractionSchema> {
  logger.info('[API] Creating schema:', name);
  const res = await fetch('/schemas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ name, fields }),
  });
  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Failed to create schema:', res.status, res.statusText);
    throw new Error('Failed to create schema');
  }
  return res.json();
}

export async function updateSchemaApi(id: string, name: string, fields: SchemaField[]): Promise<ExtractionSchema> {
  logger.info('[API] Updating schema:', id);
  const res = await fetch(`/schemas/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ name, fields }),
  });
  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Failed to update schema:', res.status, res.statusText);
    throw new Error('Failed to update schema');
  }
  return res.json();
}

export async function deleteSchemaApi(id: string): Promise<void> {
  logger.info('[API] Deleting schema:', id);
  const res = await fetch(`/schemas/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    handleUnauthorized(res);
    logger.error('[API] Failed to delete schema:', res.status, res.statusText);
    throw new Error('Failed to delete schema');
  }
}
