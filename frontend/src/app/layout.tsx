import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TechNova AI Chatbot",
  description: "Dual-Mode Agentic RAG Chatbot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
