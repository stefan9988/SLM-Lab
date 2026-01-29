import type { Conversation } from '../types';

const KEY = 'slm-conversations';

export function loadConversations(): Conversation[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]');
  } catch {
    return [];
  }
}

export function saveConversations(conversations: Conversation[]): void {
  localStorage.setItem(KEY, JSON.stringify(conversations));
}

export function addConversation(conv: Conversation): Conversation[] {
  const list = loadConversations();
  list.unshift(conv);
  saveConversations(list);
  return list;
}

export function removeConversation(id: string): Conversation[] {
  const list = loadConversations().filter((c) => c.id !== id);
  saveConversations(list);
  return list;
}
