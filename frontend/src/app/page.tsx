"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";

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

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (message: string) => {
    if (!message.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: message };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Add empty assistant message for streaming
    const assistantMessage: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) throw new Error("Failed to get response");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No reader available");

      let toolInfo: ToolInfo | undefined;
      let fullContent = "";
      let isFirstChunk = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });

        if (isFirstChunk) {
          // First chunk contains metadata JSON
          const newlineIndex = text.indexOf("\n");
          if (newlineIndex !== -1) {
            try {
              const metadata = JSON.parse(text.substring(0, newlineIndex));
              if (metadata.type === "metadata") {
                toolInfo = {
                  tool_used: metadata.tool_used,
                  sql_query: metadata.sql_query,
                  citations: metadata.citations,
                  error: metadata.error,
                };
              }
            } catch {
              // Not metadata, treat as content
              fullContent += text;
            }
            // Rest after newline is content
            fullContent += text.substring(newlineIndex + 1);
          } else {
            fullContent += text;
          }
          isFirstChunk = false;
        } else {
          fullContent += text;
        }

        // Update assistant message
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: fullContent,
            toolInfo,
          };
          return updated;
        });
      }
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
          toolInfo: { tool_used: "error" },
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <header className="flex items-center gap-3 px-6 py-4 border-b border-gray-800">
        <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center">
          <span className="text-white font-bold text-lg">T</span>
        </div>
        <div>
          <h1 className="text-lg font-semibold text-white">TechNova AI Assistant</h1>
          <p className="text-xs text-gray-400">
            Ask about policies, products, or order data
          </p>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-600/20 flex items-center justify-center mb-4">
              <span className="text-3xl">🤖</span>
            </div>
            <h2 className="text-xl font-medium text-white mb-2">
              Welcome to TechNova AI
            </h2>
            <p className="text-gray-400 max-w-md mb-6">
              I can help you with company policies, product information, and order
              data. Try asking me something!
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg">
              {[
                "What is the refund window?",
                "How many orders are pending?",
                "What is the maternity leave policy?",
                "What was total revenue last month?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSend(suggestion)}
                  className="px-4 py-2 text-sm text-gray-300 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors text-left"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </main>
  );
}
