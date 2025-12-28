import os
import glob
import sqlite3

def main():
    db_path = os.environ.get("FORGE_DB_PATH", "forge.db")
    mig_dir = os.environ.get("FORGE_MIGRATIONS_DIR", "scripts/db/migrations")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        conn.commit()
        for path in sorted(glob.glob(os.path.join(mig_dir, "*.sql"))):
            mig_id = os.path.basename(path)
            cur.execute("SELECT 1 FROM schema_migrations WHERE id = ?", (mig_id,))
            if cur.fetchone():
                continue
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
            cur.executescript(sql)
            cur.execute("INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))", (mig_id,))
            conn.commit()
            print(f"applied: {mig_id}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
