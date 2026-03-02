import { useState, useCallback, useEffect } from 'react';
import ExtractionFieldsTable from './ExtractionFieldsTable';
import PdfViewer from './PdfViewer';
import ModelSelector from './ModelSelector';
import { fetchDocumentAgentModel, updateDocumentAgentModel } from '../utils/api';
import type { HighlightRequest, ModelInfo } from '../types';

interface Props {
  onBack: () => void;
  onContinueChat?: (sessionId: string, documentName: string) => void;
}

export default function AnalyzePanel({ onBack, onContinueChat }: Props) {
  const [documentFile, setDocumentFile] = useState<{ file: File; url: string } | null>(null);
  const [highlight, setHighlight] = useState<HighlightRequest | null>(null);
  const [currentModel, setCurrentModel] = useState<ModelInfo | null>(null);
  const [modelError, setModelError] = useState(false);

  const handleLoadDocument = useCallback((file: File) => {
    setDocumentFile((prev) => {
      if (prev) URL.revokeObjectURL(prev.url);
      return { file, url: URL.createObjectURL(file) };
    });
    setHighlight(null);
  }, []);

  const handleLocationClick = useCallback(
    (req: HighlightRequest) => {
      setHighlight((prev) =>
        prev &&
        prev.pageNum === req.pageNum &&
        prev.textToHighlight === req.textToHighlight
          ? null
          : req,
      );
    },
    [],
  );

  const clearHighlight = useCallback(() => {
    setHighlight(null);
  }, []);

  useEffect(() => {
    fetchDocumentAgentModel()
      .then((m) => { setCurrentModel(m); setModelError(false); })
      .catch(() => setModelError(true));
  }, []);

  const handleModelChange = useCallback(async (provider: string, modelName: string) => {
    try {
      const updated = await updateDocumentAgentModel(provider, modelName);
      setCurrentModel(updated);
    } catch (err) {
      console.error('Failed to update document agent model:', err);
    }
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
          className="text-[#64748b] hover:text-[#e2e8f0] transition-colors duration-200"
          aria-label="Back to chat"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <h2 className="text-lg font-semibold text-[#e2e8f0]">Analyze Document</h2>
      </header>

      <div className="flex-1 flex min-h-0">
        <div className="w-2/5 border-r border-[#334155] p-5 overflow-auto">
          <ExtractionFieldsTable
            documentName={documentFile?.file.name}
            file={documentFile?.file}
            onLoadDocument={handleLoadDocument}
            onLocationClick={handleLocationClick}
            onHighlightClear={clearHighlight}
            onContinueChat={onContinueChat}
            belowControls={
              <ModelSelector
                currentProvider={currentModel?.provider ?? ''}
                currentModelName={currentModel?.modelName ?? ''}
                onModelChange={handleModelChange}
                disabled={!currentModel}
                error={modelError}
                dropDirection="down"
              />
            }
          />
        </div>
        <div className="flex-1 flex flex-col p-5">
          <PdfViewer fileUrl={documentFile?.url} highlight={highlight} />
        </div>
      </div>
    </div>
  );
}
