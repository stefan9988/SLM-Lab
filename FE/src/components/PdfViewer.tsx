import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import type { HighlightRequest } from '../types';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function normalizeForMatch(text: string): string {
  return text.replace(/\s+/g, ' ').trim().toLowerCase();
}

interface Props {
  fileUrl?: string;
  highlight?: HighlightRequest | null;
}

export default function PdfViewer({ fileUrl, highlight }: Props) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>('1');
  const containerRef = useRef<HTMLDivElement>(null);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
    setPageInput('1');
  }, []);

  const goToPage = useCallback(
    (page: number) => {
      const clamped = Math.max(1, Math.min(page, numPages));
      setPageNumber(clamped);
      setPageInput(String(clamped));
    },
    [numPages],
  );

  useEffect(() => {
    if (highlight && numPages > 0) {
      goToPage(highlight.pageNum);
    }
  }, [highlight, numPages, goToPage]);

  useEffect(() => {
    if (!highlight) return;
    const container = containerRef.current;
    if (!container) return;

    // If the mark is already in the DOM (same-page re-highlight), scroll immediately.
    const existingMark = container.querySelector('.pdf-highlight');
    if (existingMark) {
      existingMark.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // Otherwise watch for the mark to appear (text layer renders asynchronously).
    let observer: MutationObserver | null = new MutationObserver(() => {
      const mark = container.querySelector('.pdf-highlight');
      if (mark) {
        observer!.disconnect();
        observer = null;
        mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
    observer.observe(container, { subtree: true, childList: true });

    return () => {
      observer?.disconnect();
    };
  }, [highlight]);

  const customTextRenderer = useMemo(() => {
    if (!highlight) return undefined;

    const normalizedHighlight = normalizeForMatch(highlight.textToHighlight);

    return (textItem: { str: string; itemIndex: number }) => {
      if (pageNumber !== highlight.pageNum) return escapeHtml(textItem.str);

      const str = textItem.str;

      // Primary: exact/partial match within text item (existing behaviour)
      const escaped = escapeRegExp(highlight.textToHighlight);
      const exactRegex = new RegExp(`(${escaped})`, 'gi');
      const highlighted = escapeHtml(str).replace(
        exactRegex,
        '<mark class="pdf-highlight">$1</mark>',
      );
      if (highlighted !== escapeHtml(str)) return highlighted;

      // Fallback: text item is a fragment of the extraction (multi-line / formatting differences)
      const normalizedStr = normalizeForMatch(str);
      if (normalizedStr.length >= 4 && normalizedHighlight.includes(normalizedStr)) {
        return `<mark class="pdf-highlight">${escapeHtml(str)}</mark>`;
      }

      return escapeHtml(str);
    };
  }, [highlight, pageNumber]);

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPageInput(e.target.value);
  };

  const handlePageInputBlur = () => {
    const parsed = parseInt(pageInput, 10);
    if (!isNaN(parsed)) {
      goToPage(parsed);
    } else {
      setPageInput(String(pageNumber));
    }
  };

  const handlePageInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handlePageInputBlur();
    }
  };

  if (!fileUrl) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-[#64748b] gap-3">
        <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
          />
        </svg>
        <p className="text-sm">No PDF loaded</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex items-start justify-center p-4 bg-[#0a0f1e] rounded-lg"
      >
        <Document file={fileUrl} onLoadSuccess={onDocumentLoadSuccess} loading={<p className="text-[#64748b] text-sm">Loading PDF...</p>}>
          <Page pageNumber={pageNumber} width={500} customTextRenderer={customTextRenderer} />
        </Document>
      </div>

      {numPages > 0 && (
        <div className="flex items-center justify-center gap-2 py-3">
          <button
            onClick={() => goToPage(1)}
            disabled={pageNumber <= 1}
            className="px-2 py-1 rounded text-sm text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-[#1e293b] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="First page"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="19 20 9 12 19 4"/>
              <line x1="5" y1="4" x2="5" y2="20"/>
            </svg>
          </button>
          <button
            onClick={() => goToPage(pageNumber - 1)}
            disabled={pageNumber <= 1}
            className="px-2 py-1 rounded text-sm text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-[#1e293b] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Previous page"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <input
            type="text"
            value={pageInput}
            onChange={handlePageInputChange}
            onBlur={handlePageInputBlur}
            onKeyDown={handlePageInputKeyDown}
            className="w-12 text-center bg-[#1e293b] border border-[#334155] rounded text-sm text-[#e2e8f0] py-1 focus:outline-none focus:border-[#7c3aed]"
            aria-label="Page number"
          />
          <span className="text-sm text-[#64748b]">/ {numPages}</span>
          <button
            onClick={() => goToPage(pageNumber + 1)}
            disabled={pageNumber >= numPages}
            className="px-2 py-1 rounded text-sm text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-[#1e293b] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Next page"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button
            onClick={() => goToPage(numPages)}
            disabled={pageNumber >= numPages}
            className="px-2 py-1 rounded text-sm text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-[#1e293b] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Last page"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="5 4 15 12 5 20"/>
              <line x1="19" y1="4" x2="19" y2="20"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
