import type { SchemaField } from '../types';

interface Props {
  field: SchemaField;
  onChange: (updated: SchemaField) => void;
  onDelete: () => void;
}

export default function SchemaFieldRow({ field, onChange, onDelete }: Props) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={field.key}
        onChange={(e) => onChange({ ...field, key: e.target.value })}
        placeholder="Field key"
        className="flex-1 bg-[#0f172a] border border-[#334155] rounded-md px-3 py-1.5 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:border-[#7c3aed]"
      />
      <input
        type="text"
        value={field.description}
        onChange={(e) => onChange({ ...field, description: e.target.value })}
        placeholder="Description (optional)"
        className="flex-1 bg-[#0f172a] border border-[#334155] rounded-md px-3 py-1.5 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:border-[#7c3aed]"
      />
      <button
        onClick={onDelete}
        className="text-[#64748b] hover:text-[#ef4444] transition-colors duration-200 px-1"
        aria-label="Delete field"
      >
        &times;
      </button>
    </div>
  );
}
