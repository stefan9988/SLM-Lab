import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

vi.mock('./contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { name: 'Test User', email: 'test@example.com' },
    isAuthenticated: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

vi.mock('./hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    streaming: false,
    toolStatus: null,
    thinkingActive: false,
    sendMessage: vi.fn(),
    loadHistory: vi.fn(),
    stopStreaming: vi.fn(),
  }),
}));

vi.mock('./utils/storage', () => ({
  loadConversations: () => [{ id: 'conv-1', title: 'Test Conversation' }],
  addConversation: vi.fn(() => []),
  removeConversation: vi.fn(() => []),
  saveConversations: vi.fn(),
}));

vi.mock('./utils/api', () => ({
  clearHistory: vi.fn(),
  fetchSessions: vi.fn().mockResolvedValue([]),
  fetchGeneralAgentModel: vi.fn().mockResolvedValue({ provider: 'ollama', modelName: 'llama3.1:8b' }),
  updateGeneralAgentModel: vi.fn().mockResolvedValue({ provider: 'ollama', modelName: 'llama3.1:8b' }),
  fetchDocumentAgentModel: vi.fn().mockResolvedValue({ provider: 'ollama', modelName: 'llama3.1:8b' }),
  updateDocumentAgentModel: vi.fn().mockResolvedValue({ provider: 'ollama', modelName: 'llama3.1:8b' }),
  fetchSchemas: vi.fn().mockResolvedValue([]),
  createSchema: vi.fn(),
  updateSchemaApi: vi.fn(),
  deleteSchemaApi: vi.fn(),
  streamChat: vi.fn(),
  fetchHistory: vi.fn(),
}));

import * as api from './utils/api';

vi.mock('react-pdf', () => ({
  Document: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Page: () => <div data-testid="pdf-page">PDF Page</div>,
  pdfjs: { GlobalWorkerOptions: { workerSrc: '' } },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('App - model error state', () => {
  it('shows "Unavailable" in the ModelSelector when fetchGeneralAgentModel fails', async () => {
    vi.mocked(api.fetchGeneralAgentModel).mockRejectedValueOnce(new Error('Network error'));
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText('Unavailable')).toBeInTheDocument();
    });
  });
});

describe('App - analyze view navigation', () => {
  it('switches to analyze view when "Analyze Document" is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /analyze document/i }));

    expect(screen.getByRole('heading', { name: 'Analyze Document' })).toBeInTheDocument();
  });

  it('returns to chat when back button is clicked from analyze view', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /analyze document/i }));
    await user.click(screen.getByLabelText('Back to chat'));

    expect(screen.queryByRole('heading', { name: 'Analyze Document' })).not.toBeInTheDocument();
  });

  it('switches away from analyze view when "New Chat" is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /analyze document/i }));
    await user.click(screen.getByRole('button', { name: /\+ new chat/i }));

    expect(screen.queryByRole('heading', { name: 'Analyze Document' })).not.toBeInTheDocument();
  });
});
