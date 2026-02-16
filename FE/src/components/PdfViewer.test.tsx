import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import PdfViewer from './PdfViewer';

vi.mock('react-pdf', () => ({
  Document: ({ children, onLoadSuccess }: { children: React.ReactNode; onLoadSuccess?: (args: { numPages: number }) => void; file?: string }) => {
    // Simulate load on mount
    if (onLoadSuccess) {
      setTimeout(() => onLoadSuccess({ numPages: 3 }), 0);
    }
    return <div data-testid="pdf-document">{children}</div>;
  },
  Page: ({ pageNumber }: { pageNumber: number }) => (
    <div data-testid="pdf-page">Page {pageNumber}</div>
  ),
  pdfjs: { GlobalWorkerOptions: { workerSrc: '' } },
}));

describe('PdfViewer', () => {
  it('shows placeholder when no fileUrl is provided', () => {
    render(<PdfViewer />);
    expect(screen.getByText('No PDF loaded')).toBeInTheDocument();
  });

  it('renders Document and Page when fileUrl is provided', () => {
    render(<PdfViewer fileUrl="http://example.com/test.pdf" />);
    expect(screen.getByTestId('pdf-document')).toBeInTheDocument();
    expect(screen.getByTestId('pdf-page')).toBeInTheDocument();
  });

  it('renders page navigation controls when document is loaded', async () => {
    render(<PdfViewer fileUrl="http://example.com/test.pdf" />);

    // Wait for onLoadSuccess callback
    const pageInput = await screen.findByLabelText('Page number');
    expect(pageInput).toBeInTheDocument();
    expect(screen.getByTitle('First page')).toBeInTheDocument();
    expect(screen.getByTitle('Previous page')).toBeInTheDocument();
    expect(screen.getByTitle('Next page')).toBeInTheDocument();
    expect(screen.getByTitle('Last page')).toBeInTheDocument();
  });
});
