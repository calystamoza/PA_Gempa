"use client";

import { Message } from "@/lib/api";
import ReactMarkdown from "react-markdown";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`message-wrapper ${isUser ? "user" : "assistant"}`}>
      <div className={`avatar ${isUser ? "user" : "assistant"}`}>
        {isUser ? "👤" : "🌋"}
      </div>
      <div className={`bubble ${isUser ? "user" : "assistant"}`}>
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>
    </div>
  );
}
