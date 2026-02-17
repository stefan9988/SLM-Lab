import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import PdfViewer from './PdfViewer';

let lastOnLoadSuccess: ((args: { numPages: number }) => void) | undefined;
let lastCustomTextRenderer:
  | ((textItem: { str: string; itemIndex: number }) => string)
  | undefined;

vi.mock('react-pdf', () => ({
  Document: ({
    children,
    onLoadSuccess,
  }: {
    children: React.ReactNode;
    onLoadSuccess?: (args: { numPages: number }) => void;
    file?: string;
  }) => {
    lastOnLoadSuccess = onLoadSuccess;
    // Simulate load on mount
    if (onLoadSuccess) {
      setTimeout(() => onLoadSuccess({ numPages: 3 }), 0);
    }
    return <div data-testid="pdf-document">{children}</div>;
  },
  Page: ({
    pageNumber,
    customTextRenderer,
  }: {
    pageNumber: number;
    customTextRenderer?: (textItem: {
      str: string;
      itemIndex: number;
    }) => string;
  }) => {
    lastCustomTextRenderer = customTextRenderer;
    return <div data-testid="pdf-page">Page {pageNumber}</div>;
  },
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

  it('accepts highlight prop without error', () => {
    expect(() => {
      render(
        <PdfViewer
          fileUrl="http://example.com/test.pdf"
          highlight={{ pageNum: 2, textToHighlight: 'hello' }}
        />,
      );
    }).not.toThrow();
  });

  it('navigates to highlight page when highlight prop is set', async () => {
    const { rerender } = render(
      <PdfViewer fileUrl="http://example.com/test.pdf" />,
    );

    // Wait for document load
    await screen.findByLabelText('Page number');

    // Simulate document loaded with 3 pages
    await act(async () => {
      lastOnLoadSuccess?.({ numPages: 3 });
    });

    // Set a highlight on page 2
    rerender(
      <PdfViewer
        fileUrl="http://example.com/test.pdf"
        highlight={{ pageNum: 2, textToHighlight: 'test text' }}
      />,
    );

    expect(screen.getByTestId('pdf-page')).toHaveTextContent('Page 2');
  });

  it('passes customTextRenderer to Page when highlight is active', async () => {
    render(
      <PdfViewer
        fileUrl="http://example.com/test.pdf"
        highlight={{ pageNum: 1, textToHighlight: 'hello' }}
      />,
    );

    // Wait for document load
    await screen.findByLabelText('Page number');

    expect(lastCustomTextRenderer).toBeDefined();
  });

  it('does not pass customTextRenderer when no highlight', async () => {
    render(<PdfViewer fileUrl="http://example.com/test.pdf" />);

    // Wait for document load
    await screen.findByLabelText('Page number');

    expect(lastCustomTextRenderer).toBeUndefined();
  });
});
