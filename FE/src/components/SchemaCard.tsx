import type { ExtractionSchema, SchemaField } from '../types';
import SchemaFieldRow from './SchemaFieldRow';

interface Props {
  schema: ExtractionSchema;
  onUpdate: (schema: ExtractionSchema) => void;
  onDelete: () => void;
  onSave: () => void;
  saving?: boolean;
}

export default function SchemaCard({ schema, onUpdate, onDelete, onSave, saving }: Props) {
  const handleNameChange = (name: string) => {
    onUpdate({ ...schema, name });
  };

  const handleFieldChange = (updated: SchemaField) => {
    onUpdate({
      ...schema,
      fields: schema.fields.map((f) => (f.id === updated.id ? updated : f)),
    });
  };

  const handleFieldDelete = (fieldId: string) => {
    onUpdate({
      ...schema,
      fields: schema.fields.filter((f) => f.id !== fieldId),
    });
  };

  const handleAddField = () => {
    onUpdate({
      ...schema,
      fields: [...schema.fields, { id: crypto.randomUUID(), key: '', description: '' }],
    });
  };

  return (
    <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5 space-y-4">
      <input
        type="text"
        value={schema.name}
        onChange={(e) => handleNameChange(e.target.value)}
        onFocus={(e) => e.target.select()}
        className="w-full bg-transparent text-lg font-semibold text-[#e2e8f0] border-b border-[#334155] pb-1 focus:outline-none focus:border-[#7c3aed]"
        aria-label="Schema name"
      />

      <div className="grid grid-cols-[1fr_1fr_auto] gap-2 text-xs text-[#64748b] font-medium uppercase tracking-wider px-1">
        <span>Key</span>
        <span>Description</span>
        <span className="w-6" />
      </div>

      <div className="space-y-2">
        {schema.fields.map((field) => (
          <SchemaFieldRow
            key={field.id}
            field={field}
            onChange={handleFieldChange}
            onDelete={() => handleFieldDelete(field.id)}
          />
        ))}
      </div>

      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handleAddField}
          className="text-sm text-[#7c3aed] hover:text-[#a78bfa] transition-colors duration-200"
        >
          + Add Field
        </button>
        <div className="flex gap-2">
          <button
            onClick={onSave}
            disabled={saving}
            className="px-4 py-1.5 rounded-lg bg-[#7c3aed] text-white text-sm font-medium hover:bg-[#6d28d9] transition-colors duration-200 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={onDelete}
            className="px-4 py-1.5 rounded-lg border border-[#334155] text-[#64748b] text-sm hover:text-[#ef4444] hover:border-[#ef4444] transition-colors duration-200"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
