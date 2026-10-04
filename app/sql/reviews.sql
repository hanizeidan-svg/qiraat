-- Reviews DB (owned by the app; never regenerated).
-- Targets reference stable content keys:
--   masala  "2-021"            reading "2-021#1"         mawdi "2-021@2:61:5"
--   qiraa   "2-021@2:61:5|قالون|2-021#1"                bayt  "458"        general ""
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE,
  display_name  TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('admin', 'reviewer')),
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS issues (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  target_type     TEXT NOT NULL CHECK (target_type IN ('masala', 'reading', 'mawdi', 'qiraa', 'bayt', 'general')),
  target_key      TEXT NOT NULL,
  masala_id       TEXT,                 -- for grouping/filtering (NULL for bayt/general)
  field           TEXT NOT NULL,
  current_value   TEXT,                 -- snapshot at report time
  proposed_value  TEXT,
  comment         TEXT,
  status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'accepted', 'rejected', 'applied')),
  content_commit  TEXT,                 -- content build the reviewer saw
  created_by      INTEGER NOT NULL REFERENCES users(id),
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  resolved_by     INTEGER REFERENCES users(id),
  resolved_at     TEXT,
  resolution_note TEXT,
  resolution_source TEXT,               -- مصدر القرار: كتاب وصفحة
  resolution_iqrar INTEGER NOT NULL DEFAULT 0   -- 1 = قرار شخصي من المراجع (منفصل عن المصادر)
);
CREATE INDEX IF NOT EXISTS ix_issues_target ON issues(target_type, target_key);
CREATE INDEX IF NOT EXISTS ix_issues_masala ON issues(masala_id);
CREATE INDEX IF NOT EXISTS ix_issues_status ON issues(status);

CREATE TABLE IF NOT EXISTS issue_comments (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id   INTEGER NOT NULL REFERENCES issues(id),
  user_id    INTEGER NOT NULL REFERENCES users(id),
  body       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
