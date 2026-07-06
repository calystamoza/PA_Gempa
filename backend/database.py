import os
import urllib.parse
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


url = urllib.parse.urlparse(DATABASE_URL)
db_pool = psycopg2.pool.ThreadedConnectionPool(
    1, 10,  # min_conn, max_conn
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
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        db_pool.putconn(conn)


def execute_write(sql: str, params=None):
    """Eksekusi INSERT/UPDATE/DELETE query."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
        conn.commit()
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)


# ─── User Management ──────────────────────────────────────────────────────────

def get_user_by_username(username: str) -> dict | None:
    """Ambil user berdasarkan username."""
    rows = execute_query(
        "SELECT id, username, password_hash, role FROM users WHERE username = %s",
        [username],
    )
    return rows[0] if rows else None


def create_user(username: str, password_hash: str, role: str = "user") -> dict | None:
    """Buat user baru. Return user dict atau None jika username sudah ada."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
                RETURNING id, username, role
                """,
                [username, password_hash, role],
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")
        conn.rollback()
        return None
    finally:
        db_pool.putconn(conn)


# ─── Session Management ───────────────────────────────────────────────────────

def create_session(session_id: str, name: str, user_id: str | None = None):
    execute_write(
        "INSERT INTO sessions (id, name, user_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        [session_id, name[:80], user_id],
    )


def get_sessions(user_id: str | None = None) -> list:
    if user_id:
        return execute_query(
            "SELECT * FROM sessions WHERE user_id = %s ORDER BY updated_at DESC LIMIT 50",
            [user_id],
        )
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


# ─── Earthquake Management ───────────────────────────────────────────────────

def get_next_earthquake_id() -> int:
    """Ambil ID berikutnya (MAX integer id + 1). Aman jika tabel kosong."""
    rows = execute_query(
        "SELECT COALESCE(MAX(id::integer), 0) + 1 AS next_id FROM earthquakes"
    )
    return int(rows[0]["next_id"]) if rows else 1

def insert_earthquake(data: dict) -> bool:
    """Insert satu baris data gempa. Return True jika berhasil."""
    try:
        execute_write(
            """
            INSERT INTO earthquakes
                (id, place, date, month, month_name, year,
                 latitude, longitude, magnitude, depth, depth_category,
                 time)
            VALUES
                (%(id)s, %(place)s, %(date)s, %(month)s,
                 %(month_name)s, %(year)s, %(latitude)s, %(longitude)s,
                 %(magnitude)s, %(depth)s, %(depth_category)s,
                 %(time)s)
            ON CONFLICT (id) DO NOTHING
            """,
            data,
        )
        return True
    except Exception as e:
        print(f"[INSERT EARTHQUAKE ERROR] {e}")
        return False


def insert_earthquakes_batch(rows: list[dict]) -> dict:
    """Insert batch data gempa. Return dict {success, skipped, failed, errors}."""
    success = 0
    skipped = 0
    failed = 0
    errors = []
    for i, row in enumerate(rows):
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO earthquakes
                        (id, place, date, month, month_name, year,
                         latitude, longitude, magnitude, depth, depth_category,
                         time)
                    VALUES
                        (%(id)s, %(place)s, %(date)s, %(month)s,
                         %(month_name)s, %(year)s, %(latitude)s, %(longitude)s,
                         %(magnitude)s, %(depth)s, %(depth_category)s,
                         %(time)s)
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
                    """,
                    row,
                )
                returned = cur.fetchone()
                if returned:
                    success += 1
                else:
                    skipped += 1
            conn.commit()
        except Exception as e:
            failed += 1
            errors.append({"row": i + 1, "error": str(e), "data": row.get("id", "?")})
            conn.rollback()
        finally:
            db_pool.putconn(conn)
    return {"success": success, "skipped": skipped, "failed": failed, "errors": errors}
