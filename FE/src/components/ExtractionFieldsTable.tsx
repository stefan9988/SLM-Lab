import { useState, useCallback, useRef, useEffect } from "react";
import { useSchemas } from "../hooks/useSchemas";
import type { ExtractionRow } from "../types";

const LAST_SCHEMA_KEY = "slm-last-schema-id";

interface Props {
  documentName?: string;
  onLoadDocument: (file: File) => void;
}

export default function ExtractionFieldsTable({
  documentName,
  onLoadDocument,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { schemas, loading } = useSchemas();
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("");
  const [rows, setRows] = useState<ExtractionRow[]>([]);

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
        location: "",
      })),
    );
  }, [loading, schemas]);

  const handleSchemaChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const schemaId = e.target.value;
      setSelectedSchemaId(schemaId);
      localStorage.setItem(LAST_SCHEMA_KEY, schemaId);

      const schema = schemas.find((s) => s.id === schemaId);
      if (schema) {
        setRows(
          schema.fields.map((f) => ({
            fieldKey: f.key,
            extraction: "",
            location: "",
          })),
        );
      } else {
        setRows([]);
      }
    },
    [schemas],
  );

  const handleRowChange = useCallback(
    (index: number, field: "extraction" | "location", value: string) => {
      setRows((prev) =>
        prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
      );
    },
    [],
  );

  const handleAnalyze = useCallback(() => {
    // No-op for now
  }, []);

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
                <tr key={i} className="border-b border-[#1e293b]">
                  <td className="py-2 px-2 text-[#e2e8f0] font-medium">
                    {row.fieldKey}
                  </td>
                  <td className="py-1 px-2">
                    <input
                      type="text"
                      value={row.extraction}
                      onChange={(e) =>
                        handleRowChange(i, "extraction", e.target.value)
                      }
                      className="w-full bg-[#0f172a] border border-[#334155] rounded px-2 py-1 text-sm text-[#e2e8f0] focus:outline-none focus:border-[#7c3aed] transition-colors"
                      placeholder="Extracted value"
                    />
                  </td>
                  <td className="py-1 px-2">
                    <input
                      type="text"
                      value={row.location}
                      onChange={(e) =>
                        handleRowChange(i, "location", e.target.value)
                      }
                      className="w-full bg-[#0f172a] border border-[#334155] rounded px-2 py-1 text-sm text-[#e2e8f0] focus:outline-none focus:border-[#7c3aed] transition-colors"
                      placeholder="Page / section"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedSchemaId && rows.length === 0 && (
        <p className="text-[#64748b] text-sm">This schema has no fields.</p>
      )}

      <button
        onClick={handleAnalyze}
        disabled={!selectedSchemaId}
        className="mt-auto w-full rounded-lg bg-[#7c3aed] text-white py-2.5 text-sm font-medium hover:bg-[#6d28d9] hover:shadow-[0_0_12px_rgba(124,58,237,0.4)] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
      >
        Analyze Document
      </button>
    </div>
  );
}
