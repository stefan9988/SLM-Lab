export interface FileAttachment {
  name: string;
  type: string;
  content?: string;
  size?: number;
  file_id?: string;
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
  type: 'token' | 'status' | 'thinking' | 'tool_use' | 'error';
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

export interface SchemaField {
  id: string;
  key: string;
  description: string;
}

export interface ExtractionSchema {
  id: string;
  name: string;
  fields: SchemaField[];
}

export interface ExtractionLocation {
  page_num: number | null;
  chunk_num: number | null;
}

export interface ExtractionRow {
  fieldKey: string;
  extraction: string;
  location: ExtractionLocation | null;
}

export interface HighlightRequest {
  pageNum: number;
  textToHighlight: string;
}

export interface ModelInfo {
  provider: string;
  modelName: string;
}

export interface ValidationResultItem {
  key: string | null;
  claim: string;
  status: 'correct' | 'incorrect' | 'not_found';
  validated_value: string | null;
  sources: string[];
}

export type ValidationResults = Record<string, ValidationResultItem>;
