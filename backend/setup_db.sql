-- ============================================
-- Setup Database Gempa Chatbot di Supabase
-- Jalankan di Supabase → SQL Editor
-- ============================================

-- 1. Tabel sessions (daftar percakapan)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT DEFAULT 'New Chat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Tabel messages (isi percakapan)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Tabel earthquakes (data gempa dari CSV)
CREATE TABLE IF NOT EXISTS earthquakes (
    id TEXT PRIMARY KEY,
    place TEXT,
    date TEXT,
    month INTEGER,
    month_name TEXT,
    year INTEGER,
    latitude FLOAT,
    longitude FLOAT,
    magnitude FLOAT,
    depth FLOAT,
    depth_category TEXT,  -- nilai: 'dangkal', 'menengah', 'dalam' (lowercase)
    time TEXT
);

-- 4. Indexes untuk performa query
CREATE INDEX IF NOT EXISTS idx_earthquakes_place ON earthquakes(place);
CREATE INDEX IF NOT EXISTS idx_earthquakes_year ON earthquakes(year);
CREATE INDEX IF NOT EXISTS idx_earthquakes_magnitude ON earthquakes(magnitude);
CREATE INDEX IF NOT EXISTS idx_earthquakes_depth_category ON earthquakes(depth_category);
CREATE INDEX IF NOT EXISTS idx_earthquakes_year_place ON earthquakes(year, place);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
