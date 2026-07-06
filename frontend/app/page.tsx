"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
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

interface UserInfo {
  user_id: string;
  username: string;
  role: "admin" | "user";
}

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  // ─── Auth Guard ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const stored = localStorage.getItem("gempabot_user");
    if (!stored) {
      router.replace("/login");
      return;
    }
    try {
      const u = JSON.parse(stored) as UserInfo;
      // Admin yang langsung buka '/' diarahkan ke /admin
      if (u.role === "admin") {
        router.replace("/admin");
        return;
      }
      setUser(u);
    } catch {
      localStorage.removeItem("gempabot_user");
      router.replace("/login");
    }
  }, [router]);

  // Scroll ke bawah setiap ada pesan baru
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleLogout = () => {
    localStorage.removeItem("gempabot_user");
    router.push("/login");
  };

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
      const res: ChatResponse = await sendMessage(query, sessionId, user?.user_id);
      if (!sessionId) {
        setSessionId(res.session_id);
        setRefreshTrigger((n) => n + 1);
      }
      const assistantMsg: Message = {
        role: "assistant",
        content: res.answer,
        validated: res.validated,
        source: res.source,
        method: res.method,
        data_count: res.data_count,
        fetched_data: res.fetched_data,
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

  if (!user) return null;

  return (
    <div className="app-shell">
      <Sidebar
        activeSession={sessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        refreshTrigger={refreshTrigger}
        userId={user.user_id}
      />

      <div className="main">
        {/* Header */}
        <div className="chat-header">
          <span className="chat-header-icon">🌋</span>
          <div style={{ flex: 1 }}>
            <div className="chat-header-title">{currentTitle}</div>
            <div className="chat-header-subtitle">
              Powered by Groq · Data Gempa Indonesia
            </div>
          </div>
          {/* User chip + logout */}
          <div className="header-user-area">
            <div className="header-user-chip">
              <span>👤</span>
              <span>{user.username}</span>
            </div>
            <button
              id="chat-logout-btn"
              className="header-logout-btn"
              onClick={handleLogout}
              title="Keluar"
            >
              Keluar
            </button>
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
