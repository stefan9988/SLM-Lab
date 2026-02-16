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

describe('App - drawer closes on sidebar navigation', () => {
  async function openDrawer(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole('button', { name: /analyze document/i }));
    expect(screen.getByRole('dialog', { name: 'Analyze Document' })).toBeInTheDocument();
  }

  it('closes drawer when "New Chat" is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await openDrawer(user);
    await user.click(screen.getByRole('button', { name: /\+ new chat/i }));

    expect(screen.queryByRole('dialog', { name: 'Analyze Document' })).not.toBeInTheDocument();
  });

  it('closes drawer when "Extraction Schemas" is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await openDrawer(user);
    await user.click(screen.getByRole('button', { name: /extraction schemas/i }));

    expect(screen.queryByRole('dialog', { name: 'Analyze Document' })).not.toBeInTheDocument();
  });

  it('closes drawer when a conversation is selected', async () => {
    const user = userEvent.setup();
    render(<App />);

    await openDrawer(user);
    await user.click(screen.getByText('Test Conversation'));

    expect(screen.queryByRole('dialog', { name: 'Analyze Document' })).not.toBeInTheDocument();
  });
});
