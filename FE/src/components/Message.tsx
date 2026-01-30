import ReactMarkdown from 'react-markdown';
import type { Message as MessageType } from '../types';

export default function Message({ role, content, files }: MessageType) {
  const isUser = role === 'human';

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
