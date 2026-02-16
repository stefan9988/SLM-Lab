import type { Conversation, AuthUser } from '../types';
import ConversationItem from './ConversationItem';

interface Props {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onOpenSchemas: () => void;
  onOpenAnalyze: () => void;
  user?: AuthUser | null;
  onLogout?: () => void;
}

export default function Sidebar({ conversations, activeId, onSelect, onNew, onDelete, onOpenSchemas, onOpenAnalyze, user, onLogout }: Props) {
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
        <button
          className="w-full mt-2 rounded-lg border border-[#334155] text-[#64748b] py-2 text-sm font-medium hover:text-[#e2e8f0] hover:border-[#7c3aed] transition-all duration-200"
          onClick={onOpenAnalyze}
        >
          Analyze Document
        </button>
        <button
          className="w-full mt-2 rounded-lg border border-[#334155] text-[#64748b] py-2 text-sm font-medium hover:text-[#e2e8f0] hover:border-[#7c3aed] transition-all duration-200"
          onClick={onOpenSchemas}
        >
          Extraction Schemas
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
      {user && (
        <div className="p-3 border-t border-[#334155]">
          <div className="flex items-center gap-2 mb-2">
            {user.picture ? (
              <img
                src={user.picture}
                alt={user.name}
                className="w-8 h-8 rounded-full"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-[#7c3aed] flex items-center justify-center text-white text-sm font-medium">
                {user.name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-[#e2e8f0] truncate">{user.name}</p>
              <p className="text-xs text-[#64748b] truncate">{user.email}</p>
            </div>
          </div>
          {onLogout && (
            <button
              className="w-full rounded-lg border border-[#334155] text-[#64748b] py-1.5 text-sm hover:text-[#ef4444] hover:bg-[#ef4444]/10 transition-colors duration-200"
              onClick={onLogout}
            >
              Sign Out
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
