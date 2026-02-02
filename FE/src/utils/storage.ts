import type { Conversation } from '../types';
import logger from './logger';

const KEY = 'slm-conversations';

export function loadConversations(): Conversation[] {
  try {
    const data = JSON.parse(localStorage.getItem(KEY) || '[]');
    logger.info('[Storage] Loaded', data.length, 'conversations from localStorage');
    return data;
  } catch (err) {
    logger.error('[Storage] Failed to load conversations:', err);
    return [];
  }
}

export function saveConversations(conversations: Conversation[]): void {
  logger.info('[Storage] Saving', conversations.length, 'conversations to localStorage');
  localStorage.setItem(KEY, JSON.stringify(conversations));
}

export function addConversation(conv: Conversation): Conversation[] {
  logger.info('[Storage] Adding conversation:', conv.id, conv.title);
  const list = loadConversations();
  list.unshift(conv);
  saveConversations(list);
  return list;
}

export function removeConversation(id: string): Conversation[] {
  logger.info('[Storage] Removing conversation:', id);
  const list = loadConversations().filter((c) => c.id !== id);
  saveConversations(list);
  return list;
}
