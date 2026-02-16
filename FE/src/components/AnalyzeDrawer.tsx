import { useEffect, useRef, useState, useCallback } from 'react';
import ExtractionFieldsTable from './ExtractionFieldsTable';
import PdfViewer from './PdfViewer';

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function AnalyzeDrawer({ open, onClose }: Props) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const [documentFile, setDocumentFile] = useState<{ file: File; url: string } | null>(null);

  const handleLoadDocument = useCallback((file: File) => {
    setDocumentFile((prev) => {
      if (prev) URL.revokeObjectURL(prev.url);
      return { file, url: URL.createObjectURL(file) };
    });
  }, []);

  useEffect(() => {
    return () => {
      if (documentFile) URL.revokeObjectURL(documentFile.url);
    };
  }, []);// eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="absolute inset-0 z-40 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} data-testid="drawer-backdrop" />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        className="relative ml-auto w-full h-full bg-[#0f172a] border-l border-[#334155] shadow-2xl flex flex-col animate-slideIn"
        role="dialog"
        aria-label="Analyze Document"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#334155]">
          <h2 className="text-lg font-semibold text-[#e2e8f0]">Analyze Document</h2>
          <button
            onClick={onClose}
            className="text-[#64748b] hover:text-[#e2e8f0] transition-colors p-1 rounded hover:bg-[#1e293b]"
            aria-label="Close drawer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content: two-panel layout */}
        <div className="flex-1 flex min-h-0">
          {/* Left panel: Schema + Extraction fields */}
          <div className="w-2/5 border-r border-[#334155] p-5 overflow-auto">
            <ExtractionFieldsTable
              documentName={documentFile?.file.name}
              onLoadDocument={handleLoadDocument}
            />
          </div>

          {/* Right panel: PDF Viewer */}
          <div className="flex-1 flex flex-col p-5">
            <PdfViewer fileUrl={documentFile?.url} />
          </div>
        </div>
      </div>
    </div>
  );
}
