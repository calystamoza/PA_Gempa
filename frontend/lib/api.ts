const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Message {
  id?: number;
  session_id?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

export interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  sql_query?: string;
  data_count?: number;
}

export async function sendMessage(
  query: string,
  session_id?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id }),
  });
  if (!res.ok) throw new Error("Gagal mengirim pesan");
  return res.json();
}

export async function getSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/sessions`);
  if (!res.ok) return [];
  return res.json();
}

export async function getHistory(session_id: string): Promise<Message[]> {
  const res = await fetch(`${API_URL}/history/${session_id}`);
  if (!res.ok) return [];
  return res.json();
}

export async function deleteSession(session_id: string): Promise<void> {
  await fetch(`${API_URL}/history/${session_id}`, { method: "DELETE" });
}
