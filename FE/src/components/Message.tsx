import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Message as MessageType } from '../types';

interface Props extends MessageType {
  isThinking?: boolean;
}

export default function Message({ role, content, files, thinking, isThinking }: Props) {
  const isUser = role === 'human';
  const [showThinking, setShowThinking] = useState(false);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        {isUser && files && files.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-block bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full"
              >
                {f.name}
              </span>
            ))}
          </div>
        )}
        {isThinking && (
          <p className="text-sm text-gray-500 italic animate-pulse">Thinking...</p>
        )}
        {!isUser && thinking && (
          <div className="mb-2">
            <button
              onClick={() => setShowThinking((v) => !v)}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <span className="inline-block transition-transform" style={{ transform: showThinking ? 'rotate(90deg)' : 'rotate(0deg)' }}>&#9654;</span>
              Thinking
            </button>
            {showThinking && (
              <div className="mt-1 pl-3 border-l-2 border-gray-300 text-sm text-gray-500 italic whitespace-pre-wrap">
                {thinking}
              </div>
            )}
            {showThinking && (
              <button
                onClick={() => setShowThinking(false)}
                className="text-xs text-gray-500 hover:text-gray-700 mt-1"
              >
                ▲ Hide thinking
              </button>
            )}
          </div>
        )}
        {isUser ? (
          content ? <p className="whitespace-pre-wrap">{content}</p> : null
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
