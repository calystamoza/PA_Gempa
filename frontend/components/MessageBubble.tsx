"use client";

import { Message } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { useState } from "react";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const [showRawData, setShowRawData] = useState(false);
  const isUser = message.role === "user";
  const showValidation =
    !isUser && message.validated !== undefined;

  return (
    <div className={`message-wrapper ${isUser ? "user" : "assistant"}`}>
      <div className={`avatar ${isUser ? "user" : "assistant"}`}>
        {isUser ? "👤" : "🌋"}
      </div>
      <div className="bubble-column">
        <div className={`bubble ${isUser ? "user" : "assistant"}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>

        {/* Badge Validasi — hanya untuk pesan assistant */}
        {showValidation && (
          <div className="validation-row">
            <span
              className={`validation-badge ${message.validated ? "valid" : "invalid"}`}
            >
              {message.validated ? "✅ Tervalidasi" : "⚠️ Dikoreksi dari DB"}
            </span>
            {message.data_count !== undefined && (
              <span className="data-badge">
                🗄️ {message.data_count} baris data
              </span>
            )}
            {message.source && (
              <span className="data-badge">
                📡 {message.source}
              </span>
            )}
            
            {/* Tombol Lihat Data */}
            {message.fetched_data && message.fetched_data.length > 0 && (
              <button 
                onClick={() => setShowRawData(!showRawData)}
                className="view-data-btn"
              >
                {showRawData ? "🙈 Sembunyikan Data" : "🔍 Lihat Data Mentah"}
              </button>
            )}
          </div>
        )}

        {/* Tabel / JSON Data Mentah */}
        {showRawData && message.fetched_data && (
          <div className="raw-data-container">
            <pre className="raw-data-json">
              {JSON.stringify(message.fetched_data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
