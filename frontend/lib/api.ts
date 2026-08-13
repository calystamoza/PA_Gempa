const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Message {
  id?: number;
  session_id?: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  validated?: boolean;
  source?: string;
  method?: string;
  data_count?: number;
  fetched_data?: any[];
  inherited_context?: string;
}

export interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  user_id?: string;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  validated: boolean;
  source: string;
  method: string;
  sql_query?: string;
  data_count?: number;
  fetched_data?: any[];
}

export interface UserSession {
  user_id: string;
  username: string;
  role: "admin" | "user";
}

export interface EarthquakeInput {
  id: string;
  province_id?: string;
  place?: string;
  date?: string;
  month?: number | null;
  month_name?: string;
  year?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  magnitude?: number | null;
  depth?: number | null;
  depth_category?: string;
  time?: string;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function login(
  username: string,
  password: string
): Promise<UserSession> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login gagal");
  }
  return res.json();
}

export async function registerUser(
  username: string,
  password: string,
  role: "admin" | "user",
  adminRole?: string
): Promise<UserSession> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (adminRole) headers["x-user-role"] = adminRole;

  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers,
    body: JSON.stringify({ username, password, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registrasi gagal");
  }
  return res.json();
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

export async function sendMessage(
  query: string,
  session_id?: string,
  user_id?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id, user_id }),
  });
  if (!res.ok) throw new Error("Gagal mengirim pesan");
  return res.json();
}

export async function getSessions(user_id?: string): Promise<Session[]> {
  const url = user_id
    ? `${API_URL}/sessions?user_id=${encodeURIComponent(user_id)}`
    : `${API_URL}/sessions`;
  const res = await fetch(url);
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

// ─── Admin: Earthquake Data ───────────────────────────────────────────────────

export async function getNextEarthquakeId(userRole: string): Promise<string> {
  try {
    const res = await fetch(`${API_URL}/admin/earthquakes/next-id`, {
      headers: { "x-user-role": userRole },
    });
    if (!res.ok) return "";
    const data = await res.json();
    return data.next_id;
  } catch {
    return "";
  }
}

export async function insertEarthquake(
  data: EarthquakeInput,
  userRole: string
): Promise<{ message: string; id: string }> {
  const res = await fetch(`${API_URL}/admin/earthquakes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-user-role": userRole,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Gagal menyimpan data gempa");
  }
  return res.json();
}

export async function uploadEarthquakeCSV(
  file: File,
  userRole: string
): Promise<{ message: string; success: number; failed: number; errors: any[] }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/admin/earthquakes/upload`, {
    method: "POST",
    headers: { "x-user-role": userRole },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Gagal upload CSV");
  }
  return res.json();
}
