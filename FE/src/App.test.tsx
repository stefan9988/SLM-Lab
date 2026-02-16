import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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
  fetchSchemas: vi.fn().mockResolvedValue([]),
  createSchema: vi.fn(),
  updateSchemaApi: vi.fn(),
  deleteSchemaApi: vi.fn(),
  streamChat: vi.fn(),
  fetchHistory: vi.fn(),
}));

vi.mock('react-pdf', () => ({
  Document: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Page: () => <div data-testid="pdf-page">PDF Page</div>,
  pdfjs: { GlobalWorkerOptions: { workerSrc: '' } },
}));

beforeEach(() => {
  vi.clearAllMocks();
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
