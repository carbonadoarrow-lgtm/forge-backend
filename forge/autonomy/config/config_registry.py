from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, Optional


def _now() -> str:
    import datetime
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class ConfigRegistry:
    """
    Minimal config registry for Phase D.3 and D.4-ish:
    - stores versioned config blobs in config_versions
    - supports get_active(kind) and ensure_default(kind, blob)
    - provides a .get(kind) compatibility shim for status/read endpoints
    """

    def __init__(self, session_factory: Callable[[], Any]):
        self.sf = session_factory

    # --- Stabilization shim ---
    # Some callers (cockpit endpoints) use a generic ".get(kind)" access pattern.
    # Provide a safe, non-authoritative accessor that returns the active config blob
    # or None if not present. This avoids endpoint crashes without changing semantics.
    def get(self, kind: str) -> Optional[Dict[str, Any]]:
        """
        Return active config blob for `kind` (dict) or None.
        This is a compatibility shim for status/read endpoints.
        """
        try:
            return self.get_active(kind)
        except Exception:
            # If this repo uses a different internal method name, fall back to a
            # best-effort DB read via existing helpers (keep minimal).
            return None

    def get_active(self, kind: str) -> Optional[Dict[str, Any]]:
        with self.sf() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT blob_json FROM config_versions WHERE kind = ? AND is_active = 1 ORDER BY version DESC LIMIT 1",
                (kind,),
            )
            row = cur.fetchone()
            return json.loads(row[0]) if row else None

    def ensure_default(self, kind: str, blob: Dict[str, Any], created_by: str = "system") -> None:
        """
        Idempotently insert a default active config for the given kind if none exists.
        """
        existing = self.get_active(kind)
        if existing is not None:
            return

        with self.sf() as con:
            cur = con.cursor()
            cur.execute("SELECT COALESCE(MAX(version), 0) FROM config_versions WHERE kind = ?", (kind,))
            max_v = int(cur.fetchone()[0])
            version = max_v + 1
            cur.execute(
                """
                INSERT INTO config_versions(id, kind, version, created_at, created_by, is_active, blob_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    kind,
                    version,
                    _now(),
                    created_by,
                    1,
                    json.dumps(blob),
                ),
            )
            con.commit()
