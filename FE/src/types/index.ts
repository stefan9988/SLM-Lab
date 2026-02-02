export interface FileAttachment {
  name: string;
  type: string;
  content: string;
  size: number;
}

export interface Message {
  id?: string;
  role: 'human' | 'ai';
  content: string | Array<{ type?: string; text?: string }>;
  files?: FileAttachment[];
  thinking?: string;
}

export interface Conversation {
  id: string;
  title: string;
}

export interface SSEEvent {
  type: 'token' | 'status' | 'thinking';
  content: string;
}
