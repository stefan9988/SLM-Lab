export interface FileAttachment {
  name: string;
  type: string;
  content: string;
  size: number;
}

export interface Message {
  role: 'human' | 'ai';
  content: string;
  files?: FileAttachment[];
}

export interface Conversation {
  id: string;
  title: string;
}

export interface SSEEvent {
  type: 'token' | 'status';
  content: string;
}
