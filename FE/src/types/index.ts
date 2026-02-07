export interface FileAttachment {
  name: string;
  type: string;
  content?: string;
  size?: number;
}

export interface ToolUsage {
  name: string;
  args: Record<string, unknown>;
}

export interface Message {
  id?: string;
  role: 'human' | 'ai';
  content: string | Array<{ type?: string; text?: string }>;
  files?: FileAttachment[];
  thinking?: string;
  tools_used?: ToolUsage[];
}

export interface Conversation {
  id: string;
  title: string;
}

export interface SSEEvent {
  type: 'token' | 'status' | 'thinking' | 'tool_use';
  content: string;
}

export interface AuthUser {
  email: string;
  name: string;
  picture: string;
}

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
