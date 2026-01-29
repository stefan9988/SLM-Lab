export interface Message {
  role: 'human' | 'ai';
  content: string;
}

export interface Conversation {
  id: string;
  title: string;
}

export interface SSEEvent {
  type: 'token' | 'status';
  content: string;
}
