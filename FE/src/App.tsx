import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Conversation, FileAttachment } from './types';
import { loadConversations, addConversation, removeConversation } from './utils/storage';
import { useChat } from './hooks/useChat';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import MessageInput from './components/MessageInput';

function App() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string>(() => {
    const saved = loadConversations();
    return saved.length > 0 ? saved[0].id : uuidv4();
  });

  const { messages, streaming, toolStatus, sendMessage, loadHistory, clearChat, stopStreaming } = useChat(activeId);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleSend = useCallback(
    (text: string, files?: FileAttachment[]) => {
      // Ensure conversation exists in sidebar
      if (!conversations.find((c) => c.id === activeId)) {
        const title = text.slice(0, 50) || 'New Chat';
        setConversations(addConversation({ id: activeId, title }));
      }
      sendMessage(text, files);
    },
    [activeId, conversations, sendMessage],
  );

  const handleNew = useCallback(() => {
    const id = uuidv4();
    setActiveId(id);
  }, []);

  const handleSelect = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const handleDelete = useCallback(
    (id: string) => {
      setConversations(removeConversation(id));
      if (id === activeId) {
        const remaining = loadConversations();
        setActiveId(remaining.length > 0 ? remaining[0].id : uuidv4());
      }
    },
    [activeId],
  );

  const handleClear = useCallback(() => {
    clearChat();
  }, [clearChat]);

  return (
    <div className="flex h-screen bg-[#0f172a] text-[#e2e8f0]">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
        onClear={handleClear}
      />
      <main className="flex-1 flex flex-col">
        <ChatWindow messages={messages} toolStatus={toolStatus} streaming={streaming} />
        <MessageInput onSend={handleSend} disabled={streaming} streaming={streaming} onStop={stopStreaming} />
      </main>
    </div>
  );
}

export default App;
