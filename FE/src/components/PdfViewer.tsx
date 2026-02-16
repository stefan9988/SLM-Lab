import { useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface Props {
  fileUrl?: string;
}

export default function PdfViewer({ fileUrl }: Props) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>('1');

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
      <div className="flex-1 overflow-auto flex items-start justify-center p-4 bg-[#0a0f1e] rounded-lg">
        <Document file={fileUrl} onLoadSuccess={onDocumentLoadSuccess} loading={<p className="text-[#64748b] text-sm">Loading PDF...</p>}>
          <Page pageNumber={pageNumber} width={500} />
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
            |&lt;
          </button>
          <button
            onClick={() => goToPage(pageNumber - 1)}
            disabled={pageNumber <= 1}
            className="px-2 py-1 rounded text-sm text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-[#1e293b] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Previous page"
          >
            &lt;
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
            &gt;
          </button>
          <button
            onClick={() => goToPage(numPages)}
            disabled={pageNumber >= numPages}
            className="px-2 py-1 rounded text-sm text-[#94a3b8] hover:text-[#e2e8f0] hover:bg-[#1e293b] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Last page"
          >
            &gt;|
          </button>
        </div>
      )}
    </div>
  );
}
