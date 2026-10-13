-- The schema as it existed before migrations were introduced.
-- Every statement is a no-op on a database that already has these tables.
CREATE TABLE IF NOT EXISTS photographers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    event_name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    total_photos INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS photos (
    id TEXT PRIMARY KEY,
    photographer_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT NOT NULL,
    original_filename TEXT,
    face_count INTEGER DEFAULT 0,
    embeddings JSONB,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photographer_id) REFERENCES photographers(id)
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    photographer_id TEXT NOT NULL,
    selfie_path TEXT,
    matched_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photographer_id) REFERENCES photographers(id)
);

CREATE TABLE IF NOT EXISTS download_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    photo_id TEXT NOT NULL,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES user_sessions(id),
    FOREIGN KEY (photo_id) REFERENCES photos(id)
);
