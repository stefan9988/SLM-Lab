import { useState, useCallback, useEffect } from 'react';
import ExtractionFieldsTable from './ExtractionFieldsTable';
import PdfViewer from './PdfViewer';

interface Props {
  onBack: () => void;
}

export default function AnalyzePanel({ onBack }: Props) {
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
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex-1 flex flex-col h-full">
      <header className="flex items-center gap-3 px-6 py-4 border-b border-[#334155]">
        <button
          onClick={onBack}
          className="text-[#64748b] hover:text-[#e2e8f0] transition-colors duration-200 text-lg"
          aria-label="Back to chat"
        >
          &larr;
        </button>
        <h2 className="text-lg font-semibold text-[#e2e8f0]">Analyze Document</h2>
      </header>

      <div className="flex-1 flex min-h-0">
        <div className="w-2/5 border-r border-[#334155] p-5 overflow-auto">
          <ExtractionFieldsTable
            documentName={documentFile?.file.name}
            file={documentFile?.file}
            onLoadDocument={handleLoadDocument}
          />
        </div>
        <div className="flex-1 flex flex-col p-5">
          <PdfViewer fileUrl={documentFile?.url} />
        </div>
      </div>
    </div>
  );
}
