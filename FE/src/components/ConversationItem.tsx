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
      role="button"
      tabIndex={0}
      className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors duration-150 ${
        active
          ? 'bg-[#7c3aed]/20 text-[#e2e8f0] border-l-2 border-[#7c3aed]'
          : 'hover:bg-[#0f3460]/50 text-[#94a3b8] border-l-2 border-transparent'
      }`}
      onClick={() => onSelect(conversation.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(conversation.id);
        }
      }}
    >
      <span className="truncate flex-1">{conversation.title}</span>
      <button
        className="ml-2 text-[#94a3b8] opacity-0 group-hover:opacity-100 hover:text-[#ef4444] shrink-0 transition-opacity duration-150"
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
