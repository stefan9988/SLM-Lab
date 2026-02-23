import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
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

  it('exact match highlights the matching portion within a text item', async () => {
    render(
      <PdfViewer
        fileUrl="http://example.com/test.pdf"
        highlight={{ pageNum: 1, textToHighlight: 'hello' }}
      />,
    );
    await screen.findByLabelText('Page number');

    const result = lastCustomTextRenderer?.({ str: 'say hello world', itemIndex: 0 });
    expect(result).toContain('<mark class="pdf-highlight">hello</mark>');
  });

  it('fallback highlights a fragment that is part of a multi-word extraction', async () => {
    render(
      <PdfViewer
        fileUrl="http://example.com/test.pdf"
        highlight={{ pageNum: 1, textToHighlight: 'John Smith' }}
      />,
    );
    await screen.findByLabelText('Page number');

    // "John" alone is a fragment of "John Smith"
    const result = lastCustomTextRenderer?.({ str: 'John', itemIndex: 0 });
    expect(result).toBe('<mark class="pdf-highlight">John</mark>');
  });

  it('fallback highlights a whitespace-normalised fragment', async () => {
    render(
      <PdfViewer
        fileUrl="http://example.com/test.pdf"
        highlight={{ pageNum: 1, textToHighlight: 'John  Smith' }}
      />,
    );
    await screen.findByLabelText('Page number');

    // Extra spaces in the text item are collapsed during normalisation
    const result = lastCustomTextRenderer?.({ str: 'John  Smith', itemIndex: 0 });
    expect(result).toContain('<mark class="pdf-highlight">');
  });

  it('fallback does not highlight short tokens (3 chars or fewer)', async () => {
    render(
      <PdfViewer
        fileUrl="http://example.com/test.pdf"
        highlight={{ pageNum: 1, textToHighlight: 'John Smith' }}
      />,
    );
    await screen.findByLabelText('Page number');

    // "ohn" is 3 chars — below the minimum length guard
    const result = lastCustomTextRenderer?.({ str: 'ohn', itemIndex: 0 });
    expect(result).not.toContain('<mark');
  });

  it('fallback does not highlight unrelated text', async () => {
    render(
      <PdfViewer
        fileUrl="http://example.com/test.pdf"
        highlight={{ pageNum: 1, textToHighlight: 'John Smith' }}
      />,
    );
    await screen.findByLabelText('Page number');

    const result = lastCustomTextRenderer?.({ str: 'Completely unrelated text', itemIndex: 0 });
    expect(result).not.toContain('<mark');
  });

  describe('scroll-to-highlight', () => {
    let scrollIntoViewMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      scrollIntoViewMock = vi.fn();
      window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;
    });

    afterEach(() => {
      // Restore original (undefined in jsdom)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (window.HTMLElement.prototype as any).scrollIntoView;
    });

    it('scrolls to mark when it appears asynchronously', async () => {
      const { container } = render(
        <PdfViewer
          fileUrl="http://example.com/test.pdf"
          highlight={{ pageNum: 1, textToHighlight: 'hello' }}
        />,
      );

      // Simulate react-pdf text layer injecting the mark into the scroll container
      const scrollContainer = container.querySelector(
        '.flex-1.overflow-auto',
      ) as HTMLElement;
      act(() => {
        const mark = document.createElement('mark');
        mark.className = 'pdf-highlight';
        mark.textContent = 'hello';
        scrollContainer.appendChild(mark);
      });

      await waitFor(() =>
        expect(scrollIntoViewMock).toHaveBeenCalledWith({
          behavior: 'smooth',
          block: 'center',
        }),
      );
    });

    it('scrolls immediately when mark is already in the DOM', async () => {
      const { container } = render(
        <PdfViewer
          fileUrl="http://example.com/test.pdf"
          highlight={{ pageNum: 1, textToHighlight: 'hello' }}
        />,
      );

      // Insert a mark before the re-render so it is already present
      const scrollContainer = container.querySelector(
        '.flex-1.overflow-auto',
      ) as HTMLElement;
      const mark = document.createElement('mark');
      mark.className = 'pdf-highlight';
      mark.textContent = 'hello';
      scrollContainer.appendChild(mark);

      // Re-render with a new highlight — the mark is already in the DOM
      act(() => {
        render(
          <PdfViewer
            fileUrl="http://example.com/test.pdf"
            highlight={{ pageNum: 1, textToHighlight: 'hello again' }}
          />,
          { container: container.parentElement! },
        );
      });

      await waitFor(() =>
        expect(scrollIntoViewMock).toHaveBeenCalledWith({
          behavior: 'smooth',
          block: 'center',
        }),
      );
    });

    it('disconnects observer when highlight changes before mark appears', async () => {
      const disconnectSpy = vi.spyOn(MutationObserver.prototype, 'disconnect');

      const { rerender } = render(
        <PdfViewer
          fileUrl="http://example.com/test.pdf"
          highlight={{ pageNum: 1, textToHighlight: 'first' }}
        />,
      );

      // Change highlight before any mark is injected — cleanup should disconnect
      act(() => {
        rerender(
          <PdfViewer
            fileUrl="http://example.com/test.pdf"
            highlight={{ pageNum: 1, textToHighlight: 'second' }}
          />,
        );
      });

      expect(disconnectSpy).toHaveBeenCalled();
      disconnectSpy.mockRestore();
    });

    it('does not scroll when highlight is null', async () => {
      render(<PdfViewer fileUrl="http://example.com/test.pdf" highlight={null} />);

      // Give effects a chance to run
      await act(async () => {
        await new Promise((r) => setTimeout(r, 50));
      });

      expect(scrollIntoViewMock).not.toHaveBeenCalled();
    });
  });
});
