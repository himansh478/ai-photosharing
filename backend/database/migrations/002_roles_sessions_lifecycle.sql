-- Separate upload keys from the guest code, tie each guest session to the photos it
-- matched, and record what is needed for de-duplication and retention.
-- Purely additive: no existing column or row is changed.

-- A "photographers" row is one event. Keys are stored as SHA-256 hashes only.
ALTER TABLE photographers ADD COLUMN IF NOT EXISTS host_key_hash TEXT;
ALTER TABLE photographers ADD COLUMN IF NOT EXISTS contributor_key_hash TEXT;
ALTER TABLE photographers ADD COLUMN IF NOT EXISTS event_type TEXT NOT NULL DEFAULT 'other';
ALTER TABLE photographers ADD COLUMN IF NOT EXISTS retention_days INTEGER;

ALTER TABLE photos ADD COLUMN IF NOT EXISTS sha256 TEXT;
ALTER TABLE photos ADD COLUMN IF NOT EXISTS model_version TEXT;

ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS consent_at TIMESTAMP;
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;

-- Which photos a guest session is allowed to open.
CREATE TABLE IF NOT EXISTS session_photos (
    session_id TEXT NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    photo_id TEXT NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    similarity REAL,
    PRIMARY KEY (session_id, photo_id)
);

CREATE INDEX IF NOT EXISTS idx_photos_event ON photos (photographer_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_photos_event_sha256
    ON photos (photographer_id, sha256) WHERE sha256 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_event ON user_sessions (photographer_id);
CREATE INDEX IF NOT EXISTS idx_session_photos_photo ON session_photos (photo_id);
CREATE INDEX IF NOT EXISTS idx_download_logs_session ON download_logs (session_id);
CREATE INDEX IF NOT EXISTS idx_download_logs_photo ON download_logs (photo_id);
