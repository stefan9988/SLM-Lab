import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AnalyzePanel from './AnalyzePanel';

const mockFetchSchemas = vi.fn();

vi.mock('../utils/api', () => ({
  fetchSchemas: (...args: unknown[]) => mockFetchSchemas(...args),
  createSchema: vi.fn(),
  updateSchemaApi: vi.fn(),
  deleteSchemaApi: vi.fn(),
}));

vi.mock('react-pdf', () => ({
  Document: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Page: () => <div data-testid="pdf-page">PDF Page</div>,
  pdfjs: { GlobalWorkerOptions: { workerSrc: '' } },
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockFetchSchemas.mockResolvedValue([]);
});

describe('AnalyzePanel', () => {
  it('renders the header with title', () => {
    render(<AnalyzePanel onBack={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Analyze Document' })).toBeInTheDocument();
  });

  it('renders back button', () => {
    render(<AnalyzePanel onBack={vi.fn()} />);

    expect(screen.getByLabelText('Back to chat')).toBeInTheDocument();
  });

  it('calls onBack when back button is clicked', async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<AnalyzePanel onBack={onBack} />);

    await user.click(screen.getByLabelText('Back to chat'));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('shows the PDF placeholder when no file is loaded', () => {
    render(<AnalyzePanel onBack={vi.fn()} />);

    expect(screen.getByText('No PDF loaded')).toBeInTheDocument();
  });
});
