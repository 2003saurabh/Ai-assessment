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
        {/* Tool badge for assistant messages */}
        {!isUser && message.toolInfo && (
          <div className="mb-2">
            <ToolBadge toolUsed={message.toolInfo.tool_used} />
          </div>
        )}

        {/* Message content */}
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

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
