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

let capturedPdfViewerProps: Record<string, unknown> = {};
let capturedExtractionTableProps: Record<string, unknown> = {};

vi.mock('./PdfViewer', () => ({
  default: (props: Record<string, unknown>) => {
    capturedPdfViewerProps = props;
    if (!props.fileUrl) {
      return <div>No PDF loaded</div>;
    }
    return <div data-testid="pdf-viewer">PDF Viewer</div>;
  },
}));

vi.mock('./ExtractionFieldsTable', () => ({
  default: (props: Record<string, unknown>) => {
    capturedExtractionTableProps = props;
    return <div data-testid="extraction-table">Extraction Table</div>;
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockFetchSchemas.mockResolvedValue([]);
  capturedPdfViewerProps = {};
  capturedExtractionTableProps = {};
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

  it('passes highlight prop to PdfViewer', () => {
    render(<AnalyzePanel onBack={vi.fn()} />);

    expect(capturedPdfViewerProps).toHaveProperty('highlight');
    expect(capturedPdfViewerProps.highlight).toBeNull();
  });

  it('passes onLocationClick to ExtractionFieldsTable', () => {
    render(<AnalyzePanel onBack={vi.fn()} />);

    expect(capturedExtractionTableProps).toHaveProperty('onLocationClick');
    expect(typeof capturedExtractionTableProps.onLocationClick).toBe('function');
  });

  it('passes onHighlightClear to ExtractionFieldsTable', () => {
    render(<AnalyzePanel onBack={vi.fn()} />);

    expect(capturedExtractionTableProps).toHaveProperty('onHighlightClear');
    expect(typeof capturedExtractionTableProps.onHighlightClear).toBe('function');
  });
});
