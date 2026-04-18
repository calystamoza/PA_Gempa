"use client";

import { useState, useEffect, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import InputBar from "@/components/InputBar";
import { sendMessage, getHistory, Message, ChatResponse } from "@/lib/api";

const SUGGESTIONS = [
  "Wilayah mana yang paling sering gempa?",
  "Tren gempa per tahun di Indonesia",
  "Rata-rata magnitudo di Jawa Barat 2023",
  "Gempa terdalam yang pernah terjadi?",
];

export default function HomePage() {
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll ke bawah setiap ada pesan baru
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleNewChat = () => {
    setSessionId(undefined);
    setMessages([]);
  };

  const handleSelectSession = async (id: string) => {
    setSessionId(id);
    const history = await getHistory(id);
    setMessages(
      history.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }))
    );
  };

  const handleSend = async (query: string) => {
    if (!query.trim() || loading) return;

    const userMsg: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendMessage(query, sessionId);
      if (!sessionId) {
        setSessionId(res.session_id);
        setRefreshTrigger((n) => n + 1);
      }
      const assistantMsg: Message = {
        role: "assistant",
        content: res.answer,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "❌ Maaf, terjadi kesalahan koneksi ke server. Pastikan backend sudah berjalan.",
        },
      ]);
    } finally {
      setLoading(false);
      setRefreshTrigger((n) => n + 1);
    }
  };

  const handleSuggestion = (text: string) => handleSend(text);

  const currentTitle =
    messages.length > 0
      ? messages[0].content.slice(0, 50)
      : "GempaBot — Asisten Data Gempa Indonesia";

  return (
    <div className="app-shell">
      <Sidebar
        activeSession={sessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        refreshTrigger={refreshTrigger}
      />

      <div className="main">
        {/* Header */}
        <div className="chat-header">
          <span className="chat-header-icon">🌋</span>
          <div>
            <div className="chat-header-title">{currentTitle}</div>
            <div className="chat-header-subtitle">
              Powered by Gemini · Data Gempa Indonesia
            </div>
          </div>
        </div>

        {/* Chat messages */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-icon">🌋</div>
              <h1 className="welcome-title">GempaBot</h1>
              <p className="welcome-sub">
                Tanyakan apa saja tentang data gempa Indonesia — statistik,
                tren, wilayah rawan, hingga gempa terkuat yang pernah tercatat.
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="suggestion-card"
                    onClick={() => handleSuggestion(s)}
                  >
                    <p>{s}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <ChatWindow messages={messages} loading={loading} />
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <InputBar onSend={handleSend} loading={loading} />
      </div>
    </div>
  );
}
