-- Supabase publishes every table in the public schema through its REST API. Without
-- row level security, anyone holding the project's public (anon) key can read or change
-- these tables directly, bypassing this application.
-- Enabling RLS with no policies denies that access. The backend connects as the table
-- owner, which is not subject to RLS, so the application itself is unaffected.
DO $$
DECLARE
    t TEXT;
    r TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['photographers', 'photos', 'user_sessions',
                             'download_logs', 'session_photos', 'schema_migrations'] LOOP
        IF EXISTS (SELECT 1 FROM pg_tables
                   WHERE schemaname = current_schema() AND tablename = t AND tableowner = current_user) THEN
            EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
            FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('REVOKE ALL ON TABLE %I FROM %I', t, r);
                END IF;
            END LOOP;
        ELSE
            RAISE NOTICE 'Skipping RLS for %: not owned by the current role', t;
        END IF;
    END LOOP;
END $$;
