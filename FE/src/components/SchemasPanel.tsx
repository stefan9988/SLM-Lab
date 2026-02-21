import { useState } from 'react';
import { useSchemas } from '../hooks/useSchemas';
import SchemaCard from './SchemaCard';
import type { ExtractionSchema } from '../types';
import { useToast } from '../contexts/ToastContext';

interface Props {
  onBack: () => void;
}

export default function SchemasPanel({ onBack }: Props) {
  const { schemas, loading, error, addSchema, deleteSchema, saveSchema } = useSchemas();
  const { addToast } = useToast();
  const [savingId, setSavingId] = useState<string | null>(null);
  const [localEdits, setLocalEdits] = useState<Record<string, ExtractionSchema>>({});

  const handleUpdate = (schema: ExtractionSchema) => {
    setLocalEdits((prev) => ({ ...prev, [schema.id]: schema }));
  };

  const handleSave = async (schema: ExtractionSchema) => {
    setSavingId(schema.id);
    try {
      await saveSchema(schema);
      setLocalEdits((prev) => {
        const next = { ...prev };
        delete next[schema.id];
        return next;
      });
      addToast('Schema saved', 'success');
    } catch {
      addToast('Failed to save schema', 'error');
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSchema(id);
      addToast('Schema deleted', 'success');
    } catch {
      addToast('Failed to delete schema', 'error');
    }
  };

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
        <h2 className="text-lg font-semibold text-[#e2e8f0] flex-1">Extraction Schemas</h2>
        <button
          onClick={addSchema}
          className="px-4 py-1.5 rounded-lg bg-[#7c3aed] text-white text-sm font-medium hover:bg-[#6d28d9] hover:shadow-[0_0_12px_rgba(124,58,237,0.4)] transition-all duration-200"
        >
          + New Schema
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {loading ? (
            <div className="text-center py-16">
              <p className="text-[#64748b] text-sm">Loading schemas...</p>
            </div>
          ) : error ? (
            <div className="text-center py-16">
              <p className="text-[#ef4444] text-sm">{error}</p>
            </div>
          ) : schemas.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-[#64748b] text-sm">No extraction schemas yet.</p>
              <p className="text-[#64748b] text-sm mt-1">
                Click "+ New Schema" to define structured fields for document extraction.
              </p>
            </div>
          ) : (
            schemas.map((schema) => (
              <SchemaCard
                key={schema.id}
                schema={localEdits[schema.id] ?? schema}
                onUpdate={handleUpdate}
                onDelete={() => handleDelete(schema.id)}
                onSave={() => handleSave(localEdits[schema.id] ?? schema)}
                saving={savingId === schema.id}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
