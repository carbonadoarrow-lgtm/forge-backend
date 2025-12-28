-- Cockpit v2 persistence tables (Phase D.3)
-- Apply with your migration runner. For SQLite: sqlite3 file.db < this.sql

PRAGMA foreign_keys = ON;

-- Runs (summary + pointers)
CREATE TABLE IF NOT EXISTS runs_v2 (
  run_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  status TEXT NOT NULL,
  env TEXT NOT NULL,
  lane TEXT NOT NULL,
  mode TEXT NOT NULL,
  job_type TEXT NOT NULL,
  requested_by TEXT,
  parent_run_id TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  last_error_json TEXT,
  run_graph_json TEXT,
  params_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_v2_status ON runs_v2(status);
CREATE INDEX IF NOT EXISTS idx_runs_v2_env_lane ON runs_v2(env, lane);
CREATE INDEX IF NOT EXISTS idx_runs_v2_created_at ON runs_v2(created_at);

-- Full state blobs (optional; if you store only summary, you can drop this)
CREATE TABLE IF NOT EXISTS run_state_v2 (
  run_id TEXT PRIMARY KEY,
  state_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES runs_v2(run_id) ON DELETE CASCADE
);

-- Events
CREATE TABLE IF NOT EXISTS run_events_v2 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES runs_v2(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_run_events_v2_run_ts ON run_events_v2(run_id, ts);

-- Leases (per-run mutual exclusion)
CREATE TABLE IF NOT EXISTS leases_v2 (
  run_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  renewed_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_leases_v2_expires_at ON leases_v2(expires_at);

-- Versioned config blobs (policy, kill switch, flags)
CREATE TABLE IF NOT EXISTS config_versions (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  created_by TEXT,
  is_active INTEGER NOT NULL DEFAULT 0,
  blob_json TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_config_kind_version ON config_versions(kind, version);
CREATE INDEX IF NOT EXISTS idx_config_kind_active ON config_versions(kind, is_active);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor_id TEXT,
  actor_role TEXT,
  action TEXT NOT NULL,
  target_id TEXT,
  result TEXT NOT NULL,
  payload_json TEXT,
  error_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

-- Daily caps counters (per env+lane, and per run)
CREATE TABLE IF NOT EXISTS daily_counters (
  day TEXT NOT NULL,
  scope TEXT NOT NULL,         -- "lane" or "run"
  scope_id TEXT NOT NULL,      -- e.g. "env:lane" or run_id
  counter_key TEXT NOT NULL,   -- e.g. "ticks"
  value INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(day, scope, scope_id, counter_key)
);
