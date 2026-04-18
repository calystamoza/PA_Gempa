"use client";

import { useRef, useState, KeyboardEvent } from "react";

interface InputBarProps {
  onSend: (query: string) => void;
  loading: boolean;
}

export default function InputBar({ onSend, loading }: InputBarProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder="Tanyakan tentang data gempa Indonesia..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          rows={1}
          disabled={loading}
          id="chat-input"
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!value.trim() || loading}
          title="Kirim (Enter)"
          id="send-button"
        >
          {loading ? "⏳" : "➤"}
        </button>
      </div>
      <p className="input-hint">
        Tekan Enter untuk kirim · Shift+Enter untuk baris baru
      </p>
    </div>
  );
}
