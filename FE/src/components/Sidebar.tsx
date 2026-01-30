import type { Conversation } from '../types';
import ConversationItem from './ConversationItem';

interface Props {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClear: () => void;
}

export default function Sidebar({ conversations, activeId, onSelect, onNew, onDelete, onClear }: Props) {
  return (
    <aside className="w-64 bg-[#16213e] border-r border-[#334155] flex flex-col h-full">
      <div className="p-4 border-b border-[#334155]">
        <h1 className="text-base font-bold text-[#e2e8f0] uppercase tracking-wider mb-3">SLM Lab</h1>
        <button
          className="w-full rounded-lg bg-[#7c3aed] text-white py-2 text-sm font-medium hover:bg-[#6d28d9] hover:shadow-[0_0_12px_rgba(124,58,237,0.4)] transition-all duration-200"
          onClick={onNew}
        >
          + New Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.map((c) => (
          <ConversationItem
            key={c.id}
            conversation={c}
            active={c.id === activeId}
            onSelect={onSelect}
            onDelete={onDelete}
          />
        ))}
      </div>
      <div className="p-3 border-t border-[#334155]">
        <button
          className="w-full rounded-lg border border-[#334155] text-[#64748b] py-1.5 text-sm hover:text-[#ef4444] hover:bg-[#ef4444]/10 transition-colors duration-200"
          onClick={onClear}
        >
          Clear Chat
        </button>
      </div>
    </aside>
  );
}
