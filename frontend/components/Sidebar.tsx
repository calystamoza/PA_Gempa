"use client";

import { useEffect, useState } from "react";
import { getSessions, deleteSession, Session } from "@/lib/api";
import Link from "next/link";

interface SidebarProps {
  activeSession?: string;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  refreshTrigger?: number;
  userId?: string;
}

export default function Sidebar({
  activeSession,
  onNewChat,
  onSelectSession,
  refreshTrigger,
  userId,
}: SidebarProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [search, setSearch] = useState("");

  const load = async () => {
    const data = await getSessions(userId);
    setSessions(data);
  };

  useEffect(() => {
    load();
  }, [refreshTrigger, userId]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeSession === id) onNewChat();
  };

  const filtered = sessions.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="sidebar-logo-icon">🌋</span>
          <span className="sidebar-logo-text">GempaBot</span>
        </div>
        <button className="new-chat-btn" onClick={onNewChat}>
          <span>✏️</span> Chat Baru
        </button>
      </div>

      <div className="sidebar-search">
        <input
          className="search-input"
          type="text"
          placeholder="🔍 Cari percakapan..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="sidebar-sessions">
        {filtered.length > 0 && (
          <div className="sessions-label">Percakapan</div>
        )}
        {filtered.map((s) => (
          <div
            key={s.id}
            className={`session-item ${activeSession === s.id ? "active" : ""}`}
            onClick={() => onSelectSession(s.id)}
          >
            <span className="session-name">💬 {s.name}</span>
            <button
              className="session-delete"
              onClick={(e) => handleDelete(e, s.id)}
              title="Hapus sesi"
            >
              🗑
            </button>
          </div>
        ))}
        {filtered.length === 0 && (
          <p style={{ textAlign: "center", color: "var(--text-muted)", fontSize: 12, padding: "20px 0" }}>
            {search ? "Tidak ada hasil" : "Belum ada percakapan"}
          </p>
        )}
      </div>

      <div className="sidebar-footer">
        <Link href="/info" className="info-link">
          <span>ℹ️</span> Tentang GempaBot
        </Link>
      </div>
    </aside>
  );
}
