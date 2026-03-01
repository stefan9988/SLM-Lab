import React, { useState, useCallback, useRef, useEffect } from "react";
import AutoResizeTextarea from "./AutoResizeTextarea";
import { v4 as uuidv4 } from "uuid";
import { useSchemas } from "../hooks/useSchemas";
import { streamAnalyzeDocument, streamValidate, fetchValidationResults } from "../utils/api";
import type { ExtractionRow, ExtractionLocation, HighlightRequest, ValidationResults } from "../types";

const LAST_SCHEMA_KEY = "slm-last-schema-id";
const MAX_VALIDATION_URLS = 5;

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
  const validationAbortRef = useRef<AbortController | null>(null);
  const { schemas, loading } = useSchemas();
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("");
  const [rows, setRows] = useState<ExtractionRow[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [analysisSessionId, setAnalysisSessionId] = useState<string | null>(null);
  const [validationUrls, setValidationUrls] = useState<string[]>([""]);
  const [validationResults, setValidationResults] = useState<ValidationResults>({});
  const [validating, setValidating] = useState(false);
  const [validationStatusText, setValidationStatusText] = useState("");
  const [validationError, setValidationError] = useState("");
  const [showValidationPanel, setShowValidationPanel] = useState(false);

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

  // Load persisted validation results when analysisSessionId becomes available
  useEffect(() => {
    if (!analysisSessionId) return;
    fetchValidationResults(analysisSessionId).then((items) => {
      if (!items) return;
      const mapped: ValidationResults = {};
      for (const item of items) {
        const key = item.claim.split(": ")[0];
        mapped[key] = item;
      }
      setValidationResults(mapped);
    });
  }, [analysisSessionId]);

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
    setValidationResults({});
    setValidationUrls([""]);
    setValidationStatusText("");
    setValidationError("");
    setShowValidationPanel(false);
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
    setRows((prev) =>
      prev.map((row) => ({ ...row, extraction: "", location: null })),
    );
    setAnalysisSessionId(null);
    setValidationResults({});
    setValidationUrls([""]);
    setValidationStatusText("");
    setValidationError("");
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

  const handleValidate = useCallback(async () => {
    if (!analysisSessionId || validating) return;

    const validUrls = validationUrls.filter((u) => u.trim() !== "");
    if (validUrls.length === 0) return;

    const extractedData = rows
      .filter((r) => r.extraction.trim() !== "")
      .map((r) => ({ key: r.fieldKey, value: r.extraction }));

    if (extractedData.length === 0) return;

    validationAbortRef.current?.abort();
    const abort = new AbortController();
    validationAbortRef.current = abort;

    setValidating(true);
    setValidationStatusText("Starting validation...");
    setValidationError("");

    try {
      for await (const event of streamValidate(
        analysisSessionId,
        validUrls,
        extractedData,
        abort.signal,
      )) {
        if (event === "DONE") break;

        if (typeof event === "object") {
          if (event.type === "status") {
            setValidationStatusText(event.content as string);
          } else if (event.type === "validation_complete") {
            const items = event.content as import("../types").ValidationResultItem[];
            const mapped: ValidationResults = {};
            for (const item of items) {
              const key = item.claim.split(": ")[0];
              mapped[key] = item;
            }
            setValidationResults(mapped);
          } else if (event.type === "error") {
            setValidationError(`Error: ${event.content}`);
          }
        }
      }
    } catch (err) {
      if (!abort.signal.aborted) {
        setValidationError(
          `Error: ${err instanceof Error ? err.message : "Validation failed"}`,
        );
      }
    } finally {
      setValidating(false);
      setValidationStatusText("");
      validationAbortRef.current = null;
    }
  }, [analysisSessionId, validating, validationUrls, rows]);

  // Cleanup aborts on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      validationAbortRef.current?.abort();
    };
  }, []);

  const canAnalyze = !!file && !!selectedSchemaId && !analyzing;
  const hasExtractedData = rows.some((r) => r.extraction.trim() !== "");
  const hasValidation = Object.keys(validationResults).length > 0;
  const canValidate =
    !!analysisSessionId &&
    !analyzing &&
    !validating &&
    validationUrls.some((u) => u.trim() !== "") &&
    hasExtractedData;

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
                <th
                  className={`text-left py-2 px-2 border-b border-[#334155] ${hasValidation ? "w-[30%]" : "w-[37.5%]"}`}
                >
                  Extraction
                </th>
                <th
                  className={`text-left py-2 px-2 border-b border-[#334155] ${hasValidation ? "w-[30%]" : "w-[37.5%]"}`}
                >
                  Location
                </th>
                {hasValidation && (
                  <th className="text-left py-2 px-2 border-b border-[#334155] w-[15%]">
                    Source
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                const vr = validationResults[row.fieldKey];
                return (
                  <tr key={row.fieldKey} className="border-b border-[#1e293b]">
                    <td className="py-2 px-2 text-[#e2e8f0] font-medium align-top">
                      <span>{row.fieldKey}</span>
                      {vr && (
                        <span
                          className={`inline-block w-2 h-2 rounded-full ml-2 align-middle ${
                            vr.status === "correct"
                              ? "bg-green-400"
                              : vr.status === "incorrect"
                                ? "bg-red-400"
                                : "bg-yellow-400"
                          }`}
                          title={vr.validated_value ?? "Not found"}
                        />
                      )}
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
                    {hasValidation && (
                      <td className="py-2 px-2 text-xs text-[#94a3b8] align-top">
                        {vr?.sources[0] ? (
                          <a
                            href={vr.sources[0]}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#7c3aed] hover:underline truncate block max-w-[140px]"
                            title={vr.sources[0]}
                          >
                            {(() => {
                              try {
                                return new URL(vr.sources[0]).hostname;
                              } catch {
                                return vr.sources[0];
                              }
                            })()}
                          </a>
                        ) : (
                          "–"
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
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

      {!analysisSessionId ? (
        <button
          onClick={handleAnalyze}
          disabled={!canAnalyze}
          className="mt-auto w-full rounded-lg bg-[#7c3aed] text-white py-2.5 text-sm font-medium hover:bg-[#6d28d9] hover:shadow-[0_0_12px_rgba(124,58,237,0.4)] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
        >
          {analyzing ? statusText || "Analyzing..." : "Analyze Document"}
        </button>
      ) : (
        <div className="mt-auto flex flex-col gap-3">
          <button
            type="button"
            onClick={() => setShowValidationPanel((prev) => !prev)}
            data-testid="validate-toggle-button"
            className="w-full rounded-lg bg-[#7c3aed] text-white py-2.5 text-sm font-medium hover:bg-[#6d28d9] hover:shadow-[0_0_12px_rgba(124,58,237,0.4)] transition-all duration-200"
          >
            {showValidationPanel ? "Validate ▴" : "Validate ▾"}
          </button>

          {showValidationPanel && (
            <div className="border-t border-[#334155] pt-3 flex flex-col gap-2">
              <label className="block text-xs text-[#94a3b8]">
                Validation URLs
              </label>
              <div className="flex flex-col gap-1">
                {validationUrls.map((url, idx) => (
                  <div key={idx} className="flex gap-1 items-center">
                    <input
                      type="url"
                      value={url}
                      onChange={(e) => {
                        const next = [...validationUrls];
                        next[idx] = e.target.value;
                        setValidationUrls(next);
                      }}
                      placeholder="https://example.com"
                      className="flex-1 bg-[#1e293b] border border-[#334155] rounded px-2 py-1 text-sm text-[#e2e8f0] focus:outline-none focus:border-[#7c3aed] transition-colors"
                      data-testid={`validation-url-input-${idx}`}
                    />
                    {validationUrls.length > 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          setValidationUrls((prev) =>
                            prev.filter((_, i) => i !== idx),
                          );
                        }}
                        className="text-[#64748b] hover:text-red-400 transition-colors px-1"
                        aria-label="Remove URL"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {validationUrls.length < MAX_VALIDATION_URLS && (
                <button
                  type="button"
                  onClick={() => setValidationUrls((prev) => [...prev, ""])}
                  className="text-xs text-[#64748b] hover:text-[#7c3aed] transition-colors"
                  data-testid="add-url-button"
                >
                  + Add URL
                </button>
              )}
              <button
                type="button"
                onClick={handleValidate}
                disabled={!canValidate}
                className="w-full rounded-lg border border-[#7c3aed] text-[#7c3aed] py-2 text-sm font-medium hover:bg-[#7c3aed] hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
                data-testid="validate-button"
              >
                {validating ? "Validating…" : "Run Validation"}
              </button>
              {validating && validationStatusText && (
                <p className="text-xs text-[#94a3b8]">{validationStatusText}</p>
              )}
              {validationError && (
                <p className="text-xs text-red-400">{validationError}</p>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={() =>
              onContinueChat?.(analysisSessionId, documentName ?? "document")
            }
            className="w-full rounded-lg border border-[#334155] text-[#64748b] py-2.5 text-sm font-medium hover:text-[#7c3aed] hover:border-[#7c3aed] transition-all duration-200"
          >
            Continue chatting about this document
          </button>
        </div>
      )}
    </div>
  );
}
