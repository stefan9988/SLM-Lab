import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Conversation, FileAttachment, ModelInfo } from './types';
import { loadConversations, addConversation, removeConversation, saveConversations } from './utils/storage';
import { clearHistory, fetchSessions, fetchGeneralAgentModel, updateGeneralAgentModel } from './utils/api';
import { useChat } from './hooks/useChat';
import { useAuth } from './contexts/AuthContext';
import { useToast } from './contexts/ToastContext';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import MessageInput from './components/MessageInput';
import SchemasPanel from './components/SchemasPanel';
import AnalyzePanel from './components/AnalyzePanel';
import LoginPage from './components/LoginPage';

function App() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0f172a]">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#7c3aed]" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return <AuthenticatedApp user={user} onLogout={logout} />;
}

function AuthenticatedApp({ user, onLogout }: { user: ReturnType<typeof useAuth>['user']; onLogout: () => void }) {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string>(() => {
    const saved = loadConversations();
    return saved.length > 0 ? saved[0].id : uuidv4();
  });
  const [view, setView] = useState<'chat' | 'schemas' | 'analyze'>('chat');
  const [currentModel, setCurrentModel] = useState<ModelInfo | null>(null);
  const [modelError, setModelError] = useState(false);

  const { messages, streaming, toolStatus, thinkingActive, sendMessage, loadHistory, stopStreaming } = useChat(activeId);
  const { addToast } = useToast();

  useEffect(() => {
    loadHistory();
  }, [loadHistory, activeId]);

  // Sync conversation list from backend on mount
  useEffect(() => {
    fetchSessions()
      .then((backendSessions) => {
        const local = loadConversations();
        const localIds = new Set(local.map((c) => c.id));
        const newFromBackend = backendSessions
          .filter((s) => !localIds.has(s.id))
          .map((s) => ({ id: s.id, title: s.title }));
        if (newFromBackend.length > 0) {
          const merged = [...newFromBackend, ...local];
          saveConversations(merged);
          setConversations(merged);
        }
      })
      .catch((err) => {
        console.error('Failed to sync sessions from backend:', err);
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch current general agent model on mount
  useEffect(() => {
    fetchGeneralAgentModel()
      .then((m) => { setCurrentModel(m); setModelError(false); })
      .catch((err) => {
        console.error('Failed to fetch general agent model:', err);
        setModelError(true);
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
    setView('chat');
  }, []);

  const handleSelect = useCallback((id: string) => {
    setActiveId(id);
    setView('chat');
  }, []);

  const handleOpenSchemas = useCallback(() => {
    setView('schemas');
  }, []);

  const handleBackToChat = useCallback(() => {
    setView('chat');
  }, []);

  const handleOpenAnalyze = useCallback(() => {
    setView('analyze');
  }, []);

  const handleContinueChat = useCallback((sessionId: string, documentName: string) => {
    if (!conversations.find((c) => c.id === sessionId)) {
      setConversations(addConversation({ id: sessionId, title: `${documentName} analysis` }));
    }
    setActiveId(sessionId);
    setView('chat');
  }, [conversations]);

  const handleModelChange = useCallback(async (provider: string, modelName: string) => {
    try {
      const updated = await updateGeneralAgentModel(provider, modelName);
      setCurrentModel(updated);
    } catch (err) {
      console.error('Failed to update general agent model:', err);
    }
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await clearHistory(id);
        addToast('Chat deleted', 'success');
      } catch (err) {
        console.error('Failed to clear history from backend:', err);
        addToast('Failed to delete chat', 'error');
      }
      setConversations(removeConversation(id));
      if (id === activeId) {
        const remaining = loadConversations();
        setActiveId(remaining.length > 0 ? remaining[0].id : uuidv4());
      }
    },
    [activeId, addToast],
  );

  return (
    <div className="flex h-screen bg-[#0f172a] text-[#e2e8f0]">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
        onOpenSchemas={handleOpenSchemas}
        onOpenAnalyze={handleOpenAnalyze}
        user={user}
        onLogout={onLogout}
      />
      <main className="flex-1 flex flex-col relative">
        {view === 'schemas' ? (
          <SchemasPanel onBack={handleBackToChat} />
        ) : view === 'analyze' ? (
          <AnalyzePanel onBack={handleBackToChat} onContinueChat={handleContinueChat} />
        ) : (
          <>
            <ChatWindow messages={messages} toolStatus={toolStatus} streaming={streaming} thinkingActive={thinkingActive} onSend={handleSend} />
            <MessageInput onSend={handleSend} disabled={streaming} streaming={streaming} onStop={stopStreaming} currentModel={currentModel} onModelChange={handleModelChange} modelError={modelError} />
          </>
        )}
      </main>
    </div>
  );
}

export default App;
