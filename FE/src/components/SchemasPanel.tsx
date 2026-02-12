import { useSchemas } from '../hooks/useSchemas';
import SchemaCard from './SchemaCard';

interface Props {
  onBack: () => void;
}

export default function SchemasPanel({ onBack }: Props) {
  const { schemas, addSchema, deleteSchema, updateSchema } = useSchemas();

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
          {schemas.length === 0 ? (
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
                schema={schema}
                onUpdate={updateSchema}
                onDelete={() => deleteSchema(schema.id)}
                onSave={() => {}}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
