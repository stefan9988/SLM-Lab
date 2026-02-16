import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AnalyzeDrawer from './AnalyzeDrawer';

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

describe('AnalyzeDrawer', () => {
  it('renders nothing when open is false', () => {
    const { container } = render(<AnalyzeDrawer open={false} onClose={vi.fn()} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders drawer content when open is true', () => {
    render(<AnalyzeDrawer open={true} onClose={vi.fn()} />);

    expect(screen.getByRole('dialog', { name: 'Analyze Document' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Analyze Document' })).toBeInTheDocument();
  });

  it('renders close button', () => {
    render(<AnalyzeDrawer open={true} onClose={vi.fn()} />);

    expect(screen.getByLabelText('Close drawer')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<AnalyzeDrawer open={true} onClose={onClose} />);

    await user.click(screen.getByLabelText('Close drawer'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when backdrop is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<AnalyzeDrawer open={true} onClose={onClose} />);

    await user.click(screen.getByTestId('drawer-backdrop'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when Escape key is pressed', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<AnalyzeDrawer open={true} onClose={onClose} />);

    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('shows the PDF placeholder when no file is loaded', () => {
    render(<AnalyzeDrawer open={true} onClose={vi.fn()} />);

    expect(screen.getByText('No PDF loaded')).toBeInTheDocument();
  });
});
