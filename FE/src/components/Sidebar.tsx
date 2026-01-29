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
    <aside className="w-64 bg-gray-50 border-r flex flex-col h-full">
      <div className="p-3 border-b">
        <button
          className="w-full rounded-lg border border-gray-300 py-2 text-sm font-medium hover:bg-gray-100"
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
      <div className="p-3 border-t">
        <button
          className="w-full rounded-lg border border-red-300 text-red-600 py-1.5 text-sm hover:bg-red-50"
          onClick={onClear}
        >
          Clear Chat
        </button>
      </div>
    </aside>
  );
}
