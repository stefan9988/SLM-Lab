import React, { useState, useCallback, useRef, useEffect } from "react";
import AutoResizeTextarea from "./AutoResizeTextarea";
import { v4 as uuidv4 } from "uuid";
import { useSchemas } from "../hooks/useSchemas";
import { streamAnalyzeDocument } from "../utils/api";
import type { ExtractionRow, ExtractionLocation, HighlightRequest } from "../types";

const LAST_SCHEMA_KEY = "slm-last-schema-id";

function formatLocation(location: ExtractionLocation | null): string {
  if (!location) return "-";
  const parts: string[] = [];
  if (location.page_num != null) parts.push(`Page ${location.page_num}`);
  if (location.chunk_num != null) parts.push(`Chunk ${location.chunk_num}`);
  return parts.length > 0 ? parts.join(", ") : "-";
}

interface Props {
  documentName?: string;
  file?: File;
  onLoadDocument: (file: File) => void;
  onLocationClick?: (req: HighlightRequest) => void;
  onHighlightClear?: () => void;
  belowControls?: React.ReactNode;
  onContinueChat?: (sessionId: string, documentName: string) => void;
}

export default function ExtractionFieldsTable({
  documentName,
  file,
  onLoadDocument,
  onLocationClick,
  onHighlightClear,
  belowControls,
  onContinueChat,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const { schemas, loading } = useSchemas();
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("");
  const [rows, setRows] = useState<ExtractionRow[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [analysisSessionId, setAnalysisSessionId] = useState<string | null>(null);

  useEffect(() => {
    if (loading || schemas.length === 0) return;
    const lastId = localStorage.getItem(LAST_SCHEMA_KEY);
    const match = lastId ? schemas.find((s) => s.id === lastId) : null;
    const schema = match || schemas[0];
    setSelectedSchemaId(schema.id);
    setRows(
      schema.fields.map((f) => ({
        fieldKey: f.key,
        extraction: "",
        location: null,
      })),
    );
  }, [loading, schemas]);

  const handleSchemaChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const schemaId = e.target.value;
      setSelectedSchemaId(schemaId);
      localStorage.setItem(LAST_SCHEMA_KEY, schemaId);
      onHighlightClear?.();

      const schema = schemas.find((s) => s.id === schemaId);
      if (schema) {
        setRows(
          schema.fields.map((f) => ({
            fieldKey: f.key,
            extraction: "",
            location: null,
          })),
        );
      } else {
        setRows([]);
      }
    },
    [schemas, onHighlightClear],
  );

  const handleRowChange = useCallback(
    (index: number, field: "extraction", value: string) => {
      setRows((prev) =>
        prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
      );
    },
    [],
  );

  const handleClear = useCallback(() => {
    setRows((prev) =>
      prev.map((row) => ({ ...row, extraction: "", location: null })),
    );
    setStatusText("");
    setAnalysisSessionId(null);
    onHighlightClear?.();
  }, [onHighlightClear]);

  const handleSaveCSV = useCallback(() => {
    const baseName = documentName
      ? documentName.replace(/\.[^.]+$/, "")
      : "document";
    const fileName = `${baseName}_analysis.csv`;

    const header = "key,extraction,location";
    const csvRows = rows.map((r) => {
      const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
      return `${esc(r.fieldKey)},${esc(r.extraction)},${esc(formatLocation(r.location))}`;
    });
    const csv = [header, ...csvRows].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  }, [rows, documentName]);

  const handleAnalyze = useCallback(async () => {
    if (!file || !selectedSchemaId || analyzing) return;

    const sessionId = uuidv4();
    onHighlightClear?.();
    // Reset rows to empty values before starting
    setRows((prev) =>
      prev.map((row) => ({ ...row, extraction: "", location: null })),
    );
    setAnalysisSessionId(null);
    setAnalyzing(true);
    setStatusText("Starting analysis...");

    const abort = new AbortController();
    abortRef.current = abort;

    let hadFatalError = false;
    try {
      for await (const event of streamAnalyzeDocument(
        file,
        selectedSchemaId,
        sessionId,
        abort.signal,
      )) {
        if (event === "DONE") break;

        if (event.type === "status") {
          setStatusText(event.content);
        } else if (event.type === "extraction") {
          const { key, extraction, location } = event.content;
          setRows((prev) => {
            const idx = prev.findIndex((r) => r.fieldKey === key);
            if (idx !== -1) {
              // Update existing row
              return prev.map((r, i) =>
                i === idx
                  ? {
                      ...r,
                      extraction: extraction ?? "",
                      location: location ?? null,
                    }
                  : r,
              );
            }
            // Append numbered variant and remove empty base key row
            const baseMatch = key.match(/^(.+)_\d+$/);
            const baseKey = baseMatch?.[1];
            const filtered = baseKey
              ? prev.filter((r) => !(r.fieldKey === baseKey && !r.extraction))
              : prev;
            return [
              ...filtered,
              {
                fieldKey: key,
                extraction: extraction ?? "",
                location: location ?? null,
              },
            ];
          });
        } else if (event.type === "error") {
          setStatusText(`Error: ${event.content}`);
        }
      }
    } catch (err) {
      hadFatalError = true;
      if (!abort.signal.aborted) {
        setStatusText(
          `Error: ${err instanceof Error ? err.message : "Analysis failed"}`,
        );
      }
    } finally {
      setAnalyzing(false);
      abortRef.current = null;
      setStatusText((prev) => (prev.startsWith("Error") ? prev : ""));
      if (!hadFatalError && !abort.signal.aborted) {
        setAnalysisSessionId(sessionId);
      }
    }
  }, [file, selectedSchemaId, analyzing, onHighlightClear]);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const canAnalyze = !!file && !!selectedSchemaId && !analyzing;

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex gap-4">
        <div className="w-1/2">
          <label className="block text-xs text-[#94a3b8] mb-1">
            Load Document
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            data-testid="file-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onLoadDocument(file);
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-full bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-2 text-sm text-left truncate text-[#e2e8f0] hover:border-[#7c3aed] focus:outline-none focus:border-[#7c3aed] transition-colors"
          >
            {documentName || "Choose File"}
          </button>
        </div>

        <div className="w-1/2">
          <label
            htmlFor="schema-select"
            className="block text-xs text-[#94a3b8] mb-1"
          >
            Extraction Schema
          </label>
          {loading ? (
            <p className="text-[#94a3b8] text-sm py-2">Loading schemas...</p>
          ) : schemas.length === 0 ? (
            <p className="text-[#94a3b8] text-sm py-2">
              No schemas available. Create one in the Schemas tab.
            </p>
          ) : (
            <select
              id="schema-select"
              value={selectedSchemaId}
              onChange={handleSchemaChange}
              className="w-full bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-2 text-sm text-[#e2e8f0] focus:outline-none focus:border-[#7c3aed] transition-colors"
            >
              {schemas.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {belowControls && (
        <div className="flex justify-start">{belowControls}</div>
      )}

      {rows.length > 0 && (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[#94a3b8] text-xs uppercase tracking-wider">
                <th className="text-left py-2 px-2 border-b border-[#334155] w-1/4">
                  Key
                </th>
                <th className="text-left py-2 px-2 border-b border-[#334155] w-[37.5%]">
                  Extraction
                </th>
                <th className="text-left py-2 px-2 border-b border-[#334155] w-[37.5%]">
                  Location
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={row.fieldKey} className="border-b border-[#1e293b]">
                  <td className="py-2 px-2 text-[#e2e8f0] font-medium align-top">
                    {row.fieldKey}
                  </td>
                  <td className="py-1 px-2">
                    <AutoResizeTextarea
                      value={row.extraction}
                      onChange={(e) =>
                        handleRowChange(i, "extraction", e.target.value)
                      }
                      className="w-full bg-[#0f172a] border border-[#334155] rounded px-2 py-1 text-sm text-[#e2e8f0] focus:outline-none focus:border-[#7c3aed] transition-colors resize-none overflow-hidden"
                      placeholder="Extracted value"
                    />
                  </td>
                  <td className="py-2 px-2 text-sm text-[#94a3b8] align-top">
                    {row.location?.page_num != null && row.extraction ? (
                      <button
                        type="button"
                        onClick={() =>
                          onLocationClick?.({
                            pageNum: row.location!.page_num!,
                            textToHighlight: row.extraction,
                          })
                        }
                        className="text-[#7c3aed] hover:underline cursor-pointer bg-transparent border-none p-0 text-sm"
                      >
                        {formatLocation(row.location)}
                      </button>
                    ) : (
                      formatLocation(row.location)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rows.length > 0 && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleClear}
            disabled={analyzing}
            className="flex-1 rounded-lg border border-[#334155] text-[#64748b] py-2 text-sm font-medium hover:text-[#e2e8f0] hover:border-[#e2e8f0] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
          >
            Clear
          </button>
          <button
            type="button"
            onClick={handleSaveCSV}
            disabled={analyzing || rows.every((r) => !r.extraction)}
            className="flex-1 rounded-lg border border-[#334155] text-[#64748b] py-2 text-sm font-medium hover:text-[#7c3aed] hover:border-[#7c3aed] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
          >
            Save as CSV
          </button>
        </div>
      )}

      {selectedSchemaId && rows.length === 0 && (
        <p className="text-[#64748b] text-sm">This schema has no fields.</p>
      )}

      {!analyzing && statusText && statusText.startsWith("Error") && (
        <p className="text-xs text-red-400">{statusText}</p>
      )}

      <button
        onClick={handleAnalyze}
        disabled={!canAnalyze}
        className="mt-auto w-full rounded-lg bg-[#7c3aed] text-white py-2.5 text-sm font-medium hover:bg-[#6d28d9] hover:shadow-[0_0_12px_rgba(124,58,237,0.4)] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
      >
        {analyzing ? statusText || "Analyzing..." : "Analyze Document"}
      </button>

      {analysisSessionId && !analyzing && (
        <button
          type="button"
          onClick={() => onContinueChat?.(analysisSessionId, documentName ?? 'document')}
          className="w-full rounded-lg border border-[#334155] text-[#64748b] py-2.5 text-sm font-medium hover:text-[#7c3aed] hover:border-[#7c3aed] transition-all duration-200"
        >
          Continue chatting about this document
        </button>
      )}
    </div>
  );
}
