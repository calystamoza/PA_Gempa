"use client";

import { Message } from "@/lib/api";
import MessageBubble from "./MessageBubble";

interface ChatWindowProps {
  messages: Message[];
  loading: boolean;
}

export default function ChatWindow({ messages, loading }: ChatWindowProps) {
  return (
    <>
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {loading && (
        <div className="message-wrapper assistant">
          <div className="avatar assistant">🌋</div>
          <div className="bubble assistant">
            <div className="typing-dots">
              <span /><span /><span />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
