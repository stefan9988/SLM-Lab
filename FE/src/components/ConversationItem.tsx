import type { Conversation } from '../types';

interface Props {
  conversation: Conversation;
  active: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function ConversationItem({ conversation, active, onSelect, onDelete }: Props) {
  return (
    <div
      className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm ${
        active ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100 text-gray-700'
      }`}
      onClick={() => onSelect(conversation.id)}
    >
      <span className="truncate flex-1">{conversation.title}</span>
      <button
        className="ml-2 text-gray-400 hover:text-red-500 shrink-0"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(conversation.id);
        }}
        title="Delete"
      >
        ×
      </button>
    </div>
  );
}
