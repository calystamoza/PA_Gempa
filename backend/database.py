import os
import urllib.parse
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Buat koneksi ke Supabase PostgreSQL dengan SSL."""
    url = urllib.parse.urlparse(DATABASE_URL)
    return psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )


def execute_query(sql: str, params=None) -> list:
    """Eksekusi SELECT query, kembalikan list of dict."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or [])
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []


def execute_write(sql: str, params=None):
    """Eksekusi INSERT/UPDATE/DELETE query."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or [])
            conn.commit()
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")


# ─── Session Management ───────────────────────────────────────────────────────

def create_session(session_id: str, name: str):
    execute_write(
        "INSERT INTO sessions (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        [session_id, name[:80]],
    )


def get_sessions() -> list:
    return execute_query(
        "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 50"
    )


def delete_session(session_id: str):
    execute_write("DELETE FROM sessions WHERE id = %s", [session_id])


def update_session_time(session_id: str):
    execute_write(
        "UPDATE sessions SET updated_at = NOW() WHERE id = %s", [session_id]
    )


# ─── Message Management ───────────────────────────────────────────────────────

def save_message(session_id: str, role: str, content: str):
    execute_write(
        "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
        [session_id, role, content],
    )
    update_session_time(session_id)


def get_messages(session_id: str) -> list:
    return execute_query(
        "SELECT * FROM messages WHERE session_id = %s ORDER BY created_at ASC",
        [session_id],
    )
