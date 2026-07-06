-- ============================================================
-- Auth Setup — GempaBot
-- Jalankan di Supabase → SQL Editor
-- ============================================================

-- 1. Tabel users (autentikasi username/password)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Tambah kolom user_id ke tabel sessions (opsional, NULL = sesi lama)
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id) ON DELETE SET NULL;

-- 3. Index performa
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- ============================================================
-- SEED: Buat user admin default (ganti password setelah deploy)
-- password_hash di bawah = bcrypt hash dari "admin123"
-- Jalankan ini hanya sekali, atau sesuaikan di aplikasi
-- ============================================================
-- INSERT INTO users (username, password_hash, role)
-- VALUES ('admin', '$2b$12$...hash_bcrypt_disini...', 'admin')
-- ON CONFLICT (username) DO NOTHING;
