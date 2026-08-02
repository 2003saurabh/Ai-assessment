"use client";

import ReactMarkdown from "react-markdown";

interface ToolInfo {
  tool_used: string;
  sql_query?: string;
  citations?: string[];
  error?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  toolInfo?: ToolInfo;
  status?: string;
}

function ToolBadge({ toolUsed }: { toolUsed: string }) {
  const config: Record<string, { label: string; color: string; icon: string }> = {
    rag: { label: "Document Search", color: "bg-green-900/50 text-green-300 border-green-700", icon: "📄" },
    sql: { label: "Database Query", color: "bg-purple-900/50 text-purple-300 border-purple-700", icon: "🗃️" },
    both: { label: "Documents + Database", color: "bg-amber-900/50 text-amber-300 border-amber-700", icon: "🔀" },
    fallback: { label: "Out of Scope", color: "bg-gray-800 text-gray-400 border-gray-600", icon: "⚠️" },
    error: { label: "Error", color: "bg-red-900/50 text-red-300 border-red-700", icon: "❌" },
  };

  const { label, color, icon } = config[toolUsed] || config.fallback;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${color}`}>
      {icon} {label}
    </span>
  );
}

function StatusIndicator({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
        <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75" />
      </svg>
      <span>{status}</span>
    </div>
  );
}

export default function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-800 text-gray-100"
        }`}
      >
        {/* Status indicator (shown while processing) */}
        {!isUser && message.status && !message.content && (
          <StatusIndicator status={message.status} />
        )}

        {/* Tool badge for assistant messages */}
        {!isUser && message.toolInfo && (
          <div className="mb-2">
            <ToolBadge toolUsed={message.toolInfo.tool_used} />
          </div>
        )}

        {/* Message content */}
        {message.content && (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {/* SQL Query display */}
        {!isUser && message.toolInfo?.sql_query && (
          <details className="mt-3 border-t border-gray-700 pt-2">
            <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
              View SQL Query
            </summary>
            <pre className="mt-1 text-xs bg-gray-900 rounded p-2 overflow-x-auto text-green-300">
              <code>{message.toolInfo.sql_query}</code>
            </pre>
          </details>
        )}

        {/* Citations display */}
        {!isUser && message.toolInfo?.citations && message.toolInfo.citations.length > 0 && (
          <div className="mt-3 border-t border-gray-700 pt-2">
            <p className="text-xs text-gray-400 mb-1">Sources:</p>
            <div className="flex flex-wrap gap-1">
              {message.toolInfo.citations.map((citation, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-900 text-gray-300"
                >
                  📎 {citation}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
