-- Seed schema for personal ops agent demo

CREATE TABLE IF NOT EXISTS bugs (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    severity    TEXT DEFAULT 'medium' CHECK (severity IN ('critical','high','medium','low')),
    status      TEXT DEFAULT 'open'   CHECK (status   IN ('open','in_progress','resolved','closed')),
    repo        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS meeting_notes (
    id         SERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    date       DATE NOT NULL,
    attendees  TEXT[],
    body       TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    assignee    TEXT,
    due_date    DATE,
    status      TEXT DEFAULT 'todo' CHECK (status IN ('todo','in_progress','done','cancelled')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data
INSERT INTO bugs (title, description, severity, status, repo) VALUES
  ('NullPointerException in auth flow', 'Crashes on login when email contains +', 'critical', 'open', 'my-app'),
  ('Slow query on dashboard load', 'SELECT * takes 8s on large datasets', 'high', 'open', 'my-app'),
  ('Typo in error message', 'Says "succesfully" instead of "successfully"', 'low', 'resolved', 'my-app');

INSERT INTO tasks (title, description, assignee, due_date, status) VALUES
  ('Deploy v2.1 to staging', 'Run migration + smoke test', 'alice', '2025-07-01', 'todo'),
  ('Write release notes', 'Cover all changes since v2.0', 'bob', '2025-06-30', 'in_progress');
