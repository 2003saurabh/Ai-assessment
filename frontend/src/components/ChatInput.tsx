"use client";

import { useState, KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-gray-800 px-6 py-4">
      <div className="flex items-end gap-3 bg-gray-800 rounded-2xl px-4 py-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about policies, products, or orders..."
          rows={1}
          className="flex-1 bg-transparent resize-none outline-none text-white placeholder-gray-500 text-sm max-h-32"
          disabled={isLoading}
          aria-label="Chat message input"
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading}
          className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-500 transition-colors"
          aria-label="Send message"
        >
          {isLoading ? (
            <svg className="w-4 h-4 animate-spin text-white" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          )}
        </button>
      </div>
      <p className="text-xs text-gray-500 mt-2 text-center">
        TechNova AI can answer questions about HR policies, product info, and order data.
      </p>
    </div>
  );
}
